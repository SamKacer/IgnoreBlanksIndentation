# Ignore Blanks Indentation Reporting 

* Author: Samuel Kacer
* NVDA compatibility: 2021.1 and beyond
* Download [stable version](https://github.com/SamKacer/IgnoreBlanksIndentation/releases/download/v0.4/ignoreBlanksIndentationReporting-0.5.nvda-addon)

## Notice: From NVDA v2023.3 onwards, this functionality is available in NVDA natively and can be toggled on in Document Formatting settings under "Ignore blank lines for line indentation reporting"

Thi s is an NVDA addon that alters the reporting of indentation by disregarding blank lines when deciding whether to report changes in indentation. It is best understood by contrasting with normal behaviour with an example.

Consider this example:

```
def foo():
	x = 42

	return x

def bar():
```

The current behaviour of NVDA is to report indentation changes for any line where the indentation has changed, even if the line is blank. So, the example would be read like:

```
def foo():
tab x = 42
no indent blank
tab return x
no indent blank
def bar():
```

The disadvantage for this behaviour is that for most programming languages, like python, a blank line has no semantic significance and is just used to visually separate lines of code with no change to the code's meaning. Therefore, by reporting the change of indentation upon entering a blank line and then reporting it again after landing on the next line is just noise that makes it harder to focus on understanding the code.

This addon aims to improve on the behaviour by ignoring blank lines when computing indentation speech, thus the example is read like this instead:

```
def foo():
tab x = 42
blank
return x

no indent def bar():
```

## Change log

### v0.5
* support for NVDA v 2023.3 onwards (note: since this NVDA version, this addon is obsolete)

### v0.4
* support NVDA version 2022.3+, including 2023.1

### version 0.3

* support NVDA version 2021.3+
* tested compatibility with NVDA 2022.1

### version 0.2

* fix crash while reading math content

### version 0.1

* Initial release

## Source code

[Source code repository](https://github.com/SamKacer/IgnoreBlanksIndentation )
