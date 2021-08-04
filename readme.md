# Ignore Blanks Indentation Reporting 

* Author: Samuel Kacer
* NVDA compatibility: 2021.1
* Download [stable version](https://github.com/SamKacer/IgnoreBlanksIndentation/releases/download/v0.1-rc1/ignoreBlanksIndentationReporting-0.1-rc3.nvda-addon)

This is an NVDA addon that alters the reporting of indentation by disregarding blank lines when deciding whether to report changes in indentation. It is best understood by contrasting with normal behavior with an example.

Consider this example:

```
def foo():
	x = 42

	return x

def bar():
```

The current behavior of NVDA is to report indentation changes for any line where the indentation has changed, even if the line is blank. So, the example would be read like:

```
def foo():
tab x = 42
no indent blank
tab return x
no indent blank
def bar():
```

The disadvantage for this behavior is that for most programming languages, like python, a blank line has no semantic significance and is just used to visually seperate lines of code with no change to the code's meaning. Therefore, by reporting the change of indentation upon entering a blank line and then reporting it again after landing on the next line is just noise that makes it harder to focus on understanding the code.

This addon aims to improve on the behavior by ignoring blank lines when computing indentation speech, thus the example is read like this instead:

```
def foo():
tab x = 42
blank
return x

no indent def bar():
```

## Change log

### version 0.1

* initial release

## Source code

[Source code repository](https://github.com/SamKacer/IgnoreBlanksIndentation )
