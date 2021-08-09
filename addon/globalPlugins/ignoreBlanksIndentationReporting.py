# ignore blanks in indentation reporting
# Copyright (C) 2021 Samuel Kacer
#GNU GENERAL PUBLIC LICENSE V2
# author: Samuel Kacer <samuel.kacer@gmail.com>
# https://github.com/SamKacer/IgnoreBlanksIndentation.git

import globalPluginHandler
import speech.speech

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		speech.speech.getTextInfoSpeech = monkeyPatchedGetTextInfoSpeech


	def terminate(self):
		speech.speech.getTextInfoSpeech = originalGetTextInfoSpeech


# save original to restore during termination
originalGetTextInfoSpeech = speech.speech.getTextInfoSpeech


LINE_END_CHARS = { '\r', '\n' }

from speech.speech import *
from speech.speech import _extendSpeechSequence_addMathForTextInfo
# same as original except this line:
# if reportIndentation and speakTextInfoState and allIndentation!=speakTextInfoState.indentationCache:
# is replaced by:
# isNotBlank = ...
# if reportIndentation and speakTextInfoState and isNotBlank and allIndentation!=speakTextInfoState.indentationCache:
# essentially also checks if the line of text isn't blank when deciding whether to recompute indentation speech and update the allIndentation cache
def monkeyPatchedGetTextInfoSpeech(
		info: textInfos.TextInfo,
		useCache: Union[bool, SpeakTextInfoState] = True,
		formatConfig: Dict[str, bool] = None,
		unit: Optional[str] = None,
		reason: OutputReason = OutputReason.QUERY,
		_prefixSpeechCommand: Optional[SpeechCommand] = None,
		onlyInitialFields: bool = False,
		suppressBlanks: bool = False
) -> Generator[SpeechSequence, None, bool]:
	onlyCache = reason == OutputReason.ONLYCACHE
	if isinstance(useCache,SpeakTextInfoState):
		speakTextInfoState=useCache
	elif useCache:
		speakTextInfoState=SpeakTextInfoState(info.obj)
	else:
		speakTextInfoState=None
	autoLanguageSwitching=config.conf['speech']['autoLanguageSwitching']
	extraDetail=unit in (textInfos.UNIT_CHARACTER,textInfos.UNIT_WORD)
	if not formatConfig:
		formatConfig=config.conf["documentFormatting"]
	formatConfig=formatConfig.copy()
	if extraDetail:
		formatConfig['extraDetail']=True
	reportIndentation=unit==textInfos.UNIT_LINE and ( formatConfig["reportLineIndentation"] or formatConfig["reportLineIndentationWithTones"])
	# For performance reasons, when navigating by paragraph or table cell, spelling errors will not be announced.
	if unit in (textInfos.UNIT_PARAGRAPH, textInfos.UNIT_CELL) and reason == OutputReason.CARET:
		formatConfig['reportSpellingErrors']=False

	#Fetch the last controlFieldStack, or make a blank one
	controlFieldStackCache=speakTextInfoState.controlFieldStackCache if speakTextInfoState else []
	formatFieldAttributesCache=speakTextInfoState.formatFieldAttributesCache if speakTextInfoState else {}
	textWithFields=info.getTextWithFields(formatConfig)
	# We don't care about node bounds, especially when comparing fields.
	# Remove them.
	for command in textWithFields:
		if not isinstance(command,textInfos.FieldCommand):
			continue
		field=command.field
		if not field:
			continue
		try:
			del field["_startOfNode"]
		except KeyError:
			pass
		try:
			del field["_endOfNode"]
		except KeyError:
			pass

	#Make a new controlFieldStack and formatField from the textInfo's initialFields
	newControlFieldStack=[]
	newFormatField=textInfos.FormatField()
	initialFields=[]
	for field in textWithFields:
		if isinstance(field,textInfos.FieldCommand) and field.command in ("controlStart","formatChange"):
			initialFields.append(field.field)
		else:
			break
	if len(initialFields)>0:
		del textWithFields[0:len(initialFields)]
	endFieldCount=0
	for field in reversed(textWithFields):
		if isinstance(field,textInfos.FieldCommand) and field.command=="controlEnd":
			endFieldCount+=1
		else:
			break
	if endFieldCount>0:
		del textWithFields[0-endFieldCount:]
	for field in initialFields:
		if isinstance(field,textInfos.ControlField):
			newControlFieldStack.append(field)
		elif isinstance(field,textInfos.FormatField):
			newFormatField.update(field)
		else:
			raise ValueError("unknown field: %s"%field)
	#Calculate how many fields in the old and new controlFieldStacks are the same
	commonFieldCount=0
	for count in range(min(len(newControlFieldStack),len(controlFieldStackCache))):
		# #2199: When comparing controlFields try using uniqueID if it exists before resorting to compairing the entire dictionary
		oldUniqueID=controlFieldStackCache[count].get('uniqueID')
		newUniqueID=newControlFieldStack[count].get('uniqueID')
		if ((oldUniqueID is not None or newUniqueID is not None) and newUniqueID==oldUniqueID) or (newControlFieldStack[count]==controlFieldStackCache[count]):
			commonFieldCount+=1
		else:
			break

	speechSequence: SpeechSequence = []
	# #2591: Only if the reason is not focus, Speak the exit of any controlFields not in the new stack.
	# We don't do this for focus because hearing "out of list", etc. isn't useful when tabbing or using quick navigation and makes navigation less efficient.
	if reason != OutputReason.FOCUS:
		endingBlock=False
		for count in reversed(range(commonFieldCount,len(controlFieldStackCache))):
			fieldSequence = info.getControlFieldSpeech(
				controlFieldStackCache[count],
				controlFieldStackCache[0:count],
				"end_removedFromControlFieldStack",
				formatConfig,
				extraDetail,
				reason=reason
			)
			if fieldSequence:
				speechSequence.extend(fieldSequence)
			if not endingBlock and reason == OutputReason.SAYALL:
				endingBlock=bool(int(controlFieldStackCache[count].get('isBlock',0)))
		if endingBlock:
			speechSequence.append(EndUtteranceCommand())
	# The TextInfo should be considered blank if we are only exiting fields (i.e. we aren't
	# entering any new fields and there is no text).
	shouldConsiderTextInfoBlank = True

	if _prefixSpeechCommand is not None:
		assert isinstance(_prefixSpeechCommand, SpeechCommand)
		speechSequence.append(_prefixSpeechCommand)

	#Get speech text for any fields that are in both controlFieldStacks, if extra detail is not requested
	if not extraDetail:
		for count in range(commonFieldCount):
			field=newControlFieldStack[count]
			fieldSequence = info.getControlFieldSpeech(
				field,
				newControlFieldStack[0:count],
				"start_inControlFieldStack",
				formatConfig,
				extraDetail,
				reason=reason
			)
			if fieldSequence:
				speechSequence.extend(fieldSequence)
				shouldConsiderTextInfoBlank = False
			if field.get("role")==controlTypes.ROLE_MATH:
				shouldConsiderTextInfoBlank = False
				_extendSpeechSequence_addMathForTextInfo(speechSequence, info, field)

	# When true, we are inside a clickable field, and should therefore not announce any more new clickable fields
	inClickable=False
	#Get speech text for any fields in the new controlFieldStack that are not in the old controlFieldStack
	for count in range(commonFieldCount,len(newControlFieldStack)):
		field=newControlFieldStack[count]
		if not inClickable and formatConfig['reportClickable']:
			states=field.get('states')
			if states and controlTypes.STATE_CLICKABLE in states:
				# We entered the most outer clickable, so announce it, if we won't be announcing anything else interesting for this field
				presCat=field.getPresentationCategory(newControlFieldStack[0:count],formatConfig,reason)
				if not presCat or presCat is field.PRESCAT_LAYOUT:
					speechSequence.append(controlTypes.stateLabels[controlTypes.STATE_CLICKABLE])
					shouldConsiderTextInfoBlank = False
				inClickable=True
		fieldSequence = info.getControlFieldSpeech(
			field,
			newControlFieldStack[0:count],
			"start_addedToControlFieldStack",
			formatConfig,
			extraDetail,
			reason=reason
		)
		if fieldSequence:
			speechSequence.extend(fieldSequence)
			shouldConsiderTextInfoBlank = False
		if field.get("role")==controlTypes.ROLE_MATH:
			shouldConsiderTextInfoBlank = False
			_extendSpeechSequence_addMathForTextInfo(speechSequence, info, field)
		commonFieldCount+=1

	#Fetch the text for format field attributes that have changed between what was previously cached, and this textInfo's initialFormatField.
	fieldSequence = info.getFormatFieldSpeech(
		newFormatField,
		formatFieldAttributesCache,
		formatConfig,
		reason=reason,
		unit=unit,
		extraDetail=extraDetail,
		initialFormat=True
	)
	if fieldSequence:
		speechSequence.extend(fieldSequence)
	language = None
	if autoLanguageSwitching:
		language=newFormatField.get('language')
		speechSequence.append(LangChangeCommand(language))
		lastLanguage=language

	def isControlEndFieldCommand(x):
		return isinstance(x, textInfos.FieldCommand) and x.command == "controlEnd"

	isWordOrCharUnit = unit in (textInfos.UNIT_CHARACTER, textInfos.UNIT_WORD)
	if onlyInitialFields or (
		isWordOrCharUnit
		and len(textWithFields) > 0
		and len(textWithFields[0]) == 1
		and all(isControlEndFieldCommand(x) for x in itertools.islice(textWithFields, 1, None))
	):
		if not onlyCache:
			if onlyInitialFields or any(isinstance(x, str) for x in speechSequence):
				yield speechSequence
			if not onlyInitialFields:
				spellingSequence = list(getSpellingSpeech(
					textWithFields[0],
					locale=language
				))
				logBadSequenceTypes(spellingSequence)
				yield spellingSequence
		if useCache:
			speakTextInfoState.controlFieldStackCache=newControlFieldStack
			speakTextInfoState.formatFieldAttributesCache=formatFieldAttributesCache
			if not isinstance(useCache,SpeakTextInfoState):
				speakTextInfoState.updateObj()
		return False

	# Similar to before, but If the most inner clickable is exited, then we allow announcing clickable for the next lot of clickable fields entered.
	inClickable=False
	#Move through the field commands, getting speech text for all controlStarts, controlEnds and formatChange commands
	#But also keep newControlFieldStack up to date as we will need it for the ends
	# Add any text to a separate list, as it must be handled differently.
	#Also make sure that LangChangeCommand objects are added before any controlField or formatField speech
	relativeSpeechSequence=[]
	inTextChunk=False
	allIndentation=""
	indentationDone=False
	for command in textWithFields:
		if isinstance(command,str):
			# Text should break a run of clickables
			inClickable=False
			if reportIndentation and not indentationDone:
				indentation,command=splitTextIndentation(command)
				# Combine all indentation into one string for later processing.
				allIndentation+=indentation
				if command:
					# There was content after the indentation, so there is no more indentation.
					indentationDone=True
			if command:
				if inTextChunk:
					relativeSpeechSequence[-1]+=command
				else:
					relativeSpeechSequence.append(command)
					inTextChunk=True
		elif isinstance(command,textInfos.FieldCommand):
			newLanguage=None
			if  command.command=="controlStart":
				# Control fields always start a new chunk, even if they have no field text.
				inTextChunk=False
				fieldSequence = []
				if not inClickable and formatConfig['reportClickable']:
					states=command.field.get('states')
					if states and controlTypes.STATE_CLICKABLE in states:
						# We have entered an outer most clickable or entered a new clickable after exiting a previous one 
						# Announce it if there is nothing else interesting about the field, but not if the user turned it off. 
						presCat=command.field.getPresentationCategory(newControlFieldStack[0:],formatConfig,reason)
						if not presCat or presCat is command.field.PRESCAT_LAYOUT:
							fieldSequence.append(controlTypes.stateLabels[controlTypes.STATE_CLICKABLE])
						inClickable=True
				fieldSequence.extend(info.getControlFieldSpeech(
					command.field,
					newControlFieldStack,
					"start_relative",
					formatConfig,
					extraDetail,
					reason=reason
				))
				newControlFieldStack.append(command.field)
			elif command.command=="controlEnd":
				# Exiting a controlField should break a run of clickables
				inClickable=False
				# Control fields always start a new chunk, even if they have no field text.
				inTextChunk=False
				fieldSequence = info.getControlFieldSpeech(
					newControlFieldStack[-1],
					newControlFieldStack[0:-1],
					"end_relative",
					formatConfig,
					extraDetail,
					reason=reason
				)
				del newControlFieldStack[-1]
				if commonFieldCount>len(newControlFieldStack):
					commonFieldCount=len(newControlFieldStack)
			elif command.command=="formatChange":
				fieldSequence = info.getFormatFieldSpeech(
					command.field,
					formatFieldAttributesCache,
					formatConfig,
					reason=reason,
					unit=unit,
					extraDetail=extraDetail
				)
				if fieldSequence:
					inTextChunk=False
				if autoLanguageSwitching:
					newLanguage=command.field.get('language')
					if lastLanguage!=newLanguage:
						# The language has changed, so this starts a new text chunk.
						inTextChunk=False
			if not inTextChunk:
				if fieldSequence:
					if autoLanguageSwitching and lastLanguage is not None:
						# Fields must be spoken in the default language.
						relativeSpeechSequence.append(LangChangeCommand(None))
						lastLanguage=None
					relativeSpeechSequence.extend(fieldSequence)
				if command.command=="controlStart" and command.field.get("role")==controlTypes.ROLE_MATH:
					_extendSpeechSequence_addMathForTextInfo(relativeSpeechSequence, info, command.field)
				if autoLanguageSwitching and newLanguage!=lastLanguage:
					relativeSpeechSequence.append(LangChangeCommand(newLanguage))
					lastLanguage=newLanguage

	isNotBlank = any(isinstance(t, str) and not all(c in LINE_END_CHARS for c in t) for t in textWithFields)
	if reportIndentation and speakTextInfoState and isNotBlank and allIndentation!=speakTextInfoState.indentationCache:
		indentationSpeech=getIndentationSpeech(allIndentation, formatConfig)
		if autoLanguageSwitching and speechSequence[-1].lang is not None:
			# Indentation must be spoken in the default language,
			# but the initial format field specified a different language.
			# Insert the indentation before the LangChangeCommand.
			langChange = speechSequence.pop()
			speechSequence.extend(indentationSpeech)
			speechSequence.append(langChange)
		else:
			speechSequence.extend(indentationSpeech)
		if speakTextInfoState: speakTextInfoState.indentationCache=allIndentation
	# Don't add this text if it is blank.
	relativeBlank=True
	for x in relativeSpeechSequence:
		if isinstance(x,str) and not isBlank(x):
			relativeBlank=False
			break
	if not relativeBlank:
		speechSequence.extend(relativeSpeechSequence)
		shouldConsiderTextInfoBlank = False

	#Finally get speech text for any fields left in new controlFieldStack that are common with the old controlFieldStack (for closing), if extra detail is not requested
	if autoLanguageSwitching and lastLanguage is not None:
		speechSequence.append(
			LangChangeCommand(None)
		)
		lastLanguage=None
	if not extraDetail:
		for count in reversed(range(min(len(newControlFieldStack),commonFieldCount))):
			fieldSequence = info.getControlFieldSpeech(
				newControlFieldStack[count],
				newControlFieldStack[0:count],
				"end_inControlFieldStack",
				formatConfig,
				extraDetail,
				reason=reason
			)
			if fieldSequence:
				speechSequence.extend(fieldSequence)
				shouldConsiderTextInfoBlank = False

	# If there is nothing that should cause the TextInfo to be considered
	# non-blank, blank should be reported, unless we are doing a say all.
	if not suppressBlanks and reason != OutputReason.SAYALL and shouldConsiderTextInfoBlank:
		# Translators: This is spoken when the line is considered blank.
		speechSequence.append(_("blank"))

	#Cache a copy of the new controlFieldStack for future use
	if useCache:
		speakTextInfoState.controlFieldStackCache=list(newControlFieldStack)
		speakTextInfoState.formatFieldAttributesCache=formatFieldAttributesCache
		if not isinstance(useCache,SpeakTextInfoState):
			speakTextInfoState.updateObj()

	if reason == OutputReason.ONLYCACHE or not speechSequence:
		return False

	yield speechSequence
	return True

