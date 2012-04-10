#!/usr/bin/python
"""
This script generates the fairly fast C code for the following function:
Given a string, see if it belongs to a known set of strings. If it does,
return a value corresponding to that string.
"""

Template_Defines = """\
#define CS1(c1)             (c1)
#define CS2(c1, c2)         (CS1(c1) | (c2 << 8))
#define CS3(c1, c2, c3)     (CS2(c1, c2) | (c3 << 16))
#define CS4(c1, c2, c3, c4) (CS3(c1, c2, c3) | (c4 << 24))

#define STR1(s) ((s)[0])
#define STR2(s) (STR1(s) | ((s)[1] << 8))
#define STR3(s) (STR2(s) | ((s)[2] << 16))
#define STR4(s) (STR3(s) | ((s)[3] << 24))

#define STR1i(s) (tolower((s)[0]))
#define STR2i(s) (STR1i(s) | (tolower((s)[1]) << 8))
#define STR3i(s) (STR2i(s) | (tolower((s)[2]) << 16))
#define STR4i(s) (STR3i(s) | (tolower((s)[3]) << 24))
"""

Template_Find_Function = """\
%s Find%s(const char *name, size_t len)
{
	uint32_t key = 0 == len ? 0 : 1 == len ? STR1i(name) :
	               2 == len ? STR2i(name) : 3 == len ? STR3i(name) : STR4i(name);
	switch (key) {
	%s
	default: return %s;
	}
}
"""

Template_Enumeration = """\
enum %s {
	%s
};
"""

Template_Selector = """\
bool %s(%s item)
{
	switch (item) {
	%s
		return true;
	default:
		return false;
	}
}
"""

# given e.g. "br" returns "Tag_Br"
def getEnumName(name, prefix):
	parts = name.replace("-", ":").split(":")
	parts = [p[0].upper() + p[1:].lower() for p in parts]
	return "_".join([prefix] + parts)

# given e.g. "abcd" returns "'a','b','c','d'"
def splitChars(chars):
	return "'" + "','".join(chars) + "'"

# creates a lookup function that works with one switch for quickly
# finding (or failing to find) the correct value
def createFastFinder(list, type, default, caseInsensitive, funcName=None):
	list = sorted(list, key=lambda a: a[0])
	output = []
	while list:
		name, value = list.pop(0)
		if len(name) < 4:
			# no further comparison is needed for names less than 4 characters in length
			output.append('case CS%d(%s): return %s;' % (len(name), splitChars(name), value))
		else:
			# for longer names, do either another quick check (up to 8 characters)
			# or use str::EqN(I) for longer names
			output.append('case CS4(%s):' % "'%s'" % "','".join(name[:4]))
			while True:
				if len(name) == 4:
					output.append("	if (4 == len) return %s;" % value)
				elif len(name) <= 8:
					rest = name[4:]
					output.append('	if (%d == len && CS%d(%s) == STR%di(name + 4)) return %s;' %
						(len(name), len(rest), splitChars(rest), len(rest), value))
				else:
					output.append('	if (%d == len && str::EqNI(name + 4, "%s", %d)) return %s;' %
						(len(name), name[4:], len(name) - 4, value))
				# reuse the same case for names that start the same
				if not list or list[0][0][:4] != name[:4]:
					break
				name, value = list.pop(0)
			output.append('	return %s;' % default)
	
	output = Template_Find_Function % (type, funcName or type, "\n	".join(output), default)
	if not caseInsensitive:
		output = output.replace("STR1i(", "STR1(").replace("STR2i(", "STR2(")
		output = output.replace("STR3i(", "STR3(").replace("STR4i(", "STR4(")
		output = output.replace("str::EqNI(", "str::EqN(")
	return output

# given e.g. list=range(6) and size=3 returns [0,1,2],[3,4,5]
def group(list, size):
	i = 0
	while list[i:]:
		yield list[i:i + size]
		i += size

# creates an enumeration that can be used as a result for the lookup function
# (which would allow to "internalize" a string)
def createTypeEnum(list, type, default):
	list = sorted(list, key=lambda a: a[0])
	parts = group([item[1] for item in list] + [default], 5)
	return Template_Enumeration % (type, ",\n	".join([", ".join(part) for part in parts]))

def createFastSelector(fullList, nameList, funcName, type):
	cases = ["case %s:" % value for (name, value) in fullList if name in nameList]
	return Template_Selector % (funcName, type, "\n	".join([" ".join(part) for part in group(cases, 4)]))

########## HTML tags and attributes ##########

# This list has been generated by instrumenting HtmlFormatter.cpp
# to dump all tags we see in a mobi file
List_HTML_Tags = "a abbr acronym area audio b base basefont blockquote body br center code col dd div dl dt em font frame guide h1 h2 h3 h4 h5 head hr html i img input lh li link mbp:pagebreak meta object ol p pagebreak param pre reference s small span strike strong style sub sup table td th title tr tt u ul video"
List_HTML_Attrs = "size href color filepos border valign rowspan colspan link vlink style face value bgcolor class id mediarecindex controls recindex title lang clear xmlns xmlns:dc width align height"
List_Align_Attrs = "left right center justify"

# these tags must all also appear in List_HTML_Tags (else they're ignored)
List_Self_Closing_Tags = "area base basefont br col frame hr img input link meta param pagebreak mbp:pagebreak"
List_Inline_Tags = "a abbr acronym b br em font i img s small span strike strong sub sup u"

########## HTML and XML entities ##########

Template_Entities_Comment = """
// map of entity names to their Unicde runes, based on
// http://en.wikipedia.org/wiki/List_of_XML_and_HTML_character_entity_references
"""

from htmlentitydefs import entitydefs
entitydefs['apos'] = "'" # only XML entity that isn't an HTML entity as well
List_HTML_Entities = []
for name, value in entitydefs.items():
	List_HTML_Entities.append((name, value[2:-1] or str(ord(value))))

########## CSS colors ##########

# array of name/value for css colors, value is what goes inside MKRGB()
# based on https://developer.mozilla.org/en/CSS/color_value
# TODO: add more colors
List_CSS_Colors = [
	("black",        "  0,  0,  0"),
	("white",        "255,255,255"),
	("gray",         "128,128,128"),
	("red",          "255,  0,  0"),
	("green",        "  0,128,  0"),
	("blue",         "  0,  0,255"),
	("yellow",       "255,255,  0"),
];
# fallback is the transparent color MKRGBA(0,0,0,0)

########## main ##########

print Template_Defines

tags = [(name, getEnumName(name, "Tag")) for name in List_HTML_Tags.split()]
print createFastFinder(tags, "HtmlTag", "Tag_NotFound", True)
print createFastSelector(tags, List_Self_Closing_Tags.split(), "IsSelfclosingTag", "HtmlTag")
print createFastSelector(tags, List_Inline_Tags.split(), "IsInlineTag", "HtmlTag")

attrs = [(name, getEnumName(name, "Attr")) for name in List_HTML_Attrs.split()]
print createFastFinder(attrs, "HtmlAttr", "Attr_NotFound", True)

aligns = [(name, getEnumName(name, "Align")) for name in List_Align_Attrs.split()]
print createFastFinder(aligns, "AlignAttr", "Align_NotFound", True)

print Template_Entities_Comment
print createFastFinder(List_HTML_Entities, "uint32_t", "-1", False, "HtmlEntityRune")

cssColors = [(name, "MKRGB(%s)" % value) for (name, value) in List_CSS_Colors]
print createFastFinder(cssColors, "ARGB", "MKRGBA(0,0,0,0)", True)

# enumerations for the header
print createTypeEnum(tags, "HtmlTag", "Tag_NotFound")
print createTypeEnum(attrs, "HtmlAttr", "Attr_NotFound")
print createTypeEnum(aligns, "AlignAttr", "Align_NotFound")
