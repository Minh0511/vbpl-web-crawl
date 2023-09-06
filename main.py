from bs4 import BeautifulSoup

# Opening the html file
HTMLFile = open("misc/vbpl.html", "r", encoding="utf8")

# Reading the file
index = HTMLFile.read()

# Creating a BeautifulSoup object and specifying the parser
S = BeautifulSoup(index, 'lxml')

# Using the select-one method to find the second element from the li tag
Tag = S.select_one('li:nth-of-type(2)')

# Using the decompose method
Tag.decompose()

# Using the prettify method to modify the code
print(S.body.prettify())
