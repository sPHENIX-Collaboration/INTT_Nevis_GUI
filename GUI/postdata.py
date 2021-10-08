import httplib
import urllib, urllib2, cookielib
import sys
from BeautifulSoup import BeautifulSoup
import re
from Tkinter import *
import tkGetPasswd

cookieJar = cookielib.CookieJar()
password_tuple = None

def postdata(url,data):
    global cookieJar
    global password_tuple
    
    # Ask user for authentication info
    if password_tuple is None:
        d = tkGetPasswd.GetPasswd(None,"Login to RCF")
        password_tuple = d.result
    if password_tuple is None:
        print 'Postdata operation cancelled'
        return 0
    else:
        username, password = password_tuple

    request = urllib2.Request(url)
    opener = urllib2.build_opener()
    f = opener.open(request)
    if f.url is not url:
        print 'WARNING: Detected a redirection'
        print 'Reading URL %s' % f.url
        html_data = f.read()
        #print html_data
        soup = BeautifulSoup(html_data)
        RT = soup.find('input',{"name": "RT"}) #Find the proper tag
        ST = soup.find('input',{"name": "ST"}) #Find the proper tag
        LC = soup.find('input',{"name": "LC"}) #Find the proper tag
        RT_value = RT['value'] #The value attribute
        ST_value = ST['value'] #The value attribute
        LC_value = LC['value'] #The value attribute
        login_data = urllib.urlencode({ 'RT': RT_value, 'ST': ST_value, 'LC': LC_value, 'username' : username, 'password' : password})
        if cookieJar is None:
            cookieJar = cookielib.CookieJar()
        cj_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar))
        resp = cj_opener.open(f.url, login_data)
        print 'Reading URL %s' % resp.url
        html_data = resp.read()
        #print html_data
    soup = BeautifulSoup(html_data)
    prot,site = url.split("://")
    href = soup.find('a',href=re.compile(site)) #Find the proper tag
    if href is None:
        print "Failed to parse HTML data from login screen. URL = ",url
        password_tuple = None
        return 0
    final_url = href['href']
    post_data = urllib.urlencode(data)
    #print final_url
    try:
        resp = cj_opener.open(final_url,post_data)
        print 'Opened URL %s' % resp.url
    except urllib2.HTTPError, e:
        print "HTTP Error while opening %s: " % final_url,e
        password_tuple = None
        return 0
    print 'Posting request to URL %s' % resp.url
    request = urllib2.Request(resp.url,post_data)
    try:
        resp2 = cj_opener.open(request)
        print 'Opened URL %s' % resp2.url
    except urllib1.HTTPError, e:
        print "HTTP Error while opening %s: "%request,e
        password_tuple = None
        return 0
    print 'Readback of URL %s:' % resp2.url
    result = resp2.read()
    print result
    if not re.search('Successfully stored data',result): 
        password_tuple = None
        return 0
    return 1
