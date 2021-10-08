import httplib
import urllib, urllib2, cookielib
import getpass
import sys
from BeautifulSoup import BeautifulSoup
import re
from Tkinter import *
import tkGetPasswd

try:
    url, id_req, size_req = sys.argv[1:4]
except ValueError, e:
    print 'ValueError:',e
    sys.exit()

#url = sys.argv[1]
#user = sys.argv[2]
#passwd = sys.argv[3]
#id_req = sys.argv[4]
#size_req = sys.argv[5]
try:
    print url, id_req, size_req
except NameError, e:
    print e
    sys.exit()

# Use our password-getter in Tk, since cygwin f's up the
# terminal settings (and it's prettier anyway)
master = Tk()
master.withdraw()
d = tkGetPasswd.GetPasswd(master,"Login to RCF")
username,password = d.result

# Open the requested URL.  The returned page is the redirected 
# webauth page.  We need to parse it for the needed input values.
request = urllib2.Request(url)
opener = urllib2.build_opener()
f = opener.open(request)
html_data = f.read()

# Create the soup object from the HTML data of the webauth page
soup = BeautifulSoup(html_data)
RT = soup.find('input',{"name": "RT"}) #Find the proper tag
ST = soup.find('input',{"name": "ST"}) #Find the proper tag
LC = soup.find('input',{"name": "LC"}) #Find the proper tag
RT_value = RT['value'] #The value attribute
ST_value = ST['value'] #The value attribute
LC_value = LC['value'] #The value attribute

# Ask(ed) the user for his/her password, and build the POST data dictionary
login_data = urllib.urlencode({ 'RT': RT_value, 'ST': ST_value, 'LC': LC_value, 'username' : username, 'password' : password})

# Post the data to the webauth login page.  This should get us
# redirected to yet another webauth page, confirming our access.  We
# need to parse this page to get the link to the final URL we wanted.
cj = cookielib.CookieJar()
cj_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
resp = cj_opener.open(f.url, login_data)
html_data = resp.read()
soup = BeautifulSoup(html_data)
prot,site = url.split("://")
href = soup.find('a',href=re.compile(site)) #Find the proper tag
final_url = href['href']

# Build the post data for the final url destination and post it.  Print
# what we get back
post_data = urllib.urlencode({'module_id': id_req, 'large_small': size_req})
resp = cj_opener.open(final_url,post_data)
request = urllib2.Request(resp.url,post_data)
resp2 = cj_opener.open(request)
print resp2.read()

sys.exit()
