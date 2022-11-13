#!/usr/bin/python
import sys
import urllib
if sys.hexversion < 0x02050000:
    import elementtree.ElementTree as CopyscapeTree # If you are on Python 2.4, please make sure the ElementTree module is installed
else:
    import xml.etree.ElementTree as CopyscapeTree

import urllib.request
import urllib.error

from project import settings

#   Python sample code for Copyscape Premium API
#   
#   Compatible with Python 2.4 or later
#   
#   You may install, use, reproduce, modify and redistribute this code, with or without
#   modifications, subject to the general Terms and Conditions on the Copyscape website. 
#   
#   For any technical assistance please contact us via our website.
#   
#   13-Jun-2013: First version
#   
#   Copyscape (c) Indigo Stream Technologies 2013 - http://www.copyscape.com/
#
#
#   Instructions for use:
#   
#   1. Set the constants COPYSCAPE_USERNAME and COPYSCAPE_API_KEY below to your details.
#   2. Call the appropriate API function, following the examples below.
#   3. The API response is in XML, which in this sample code is parsed using ElementTree and returned as a Node.
#   4. To run the examples provided, please uncomment the next line:

# COPYSCAPE_RUN_EXAMPLES=True

#   Error handling:
#   
#   * If a call failed completely (e.g. urllib.Request failed to connect), functions return None.
#   * If the API returned an error, the response Node will contain an 'error' element.


# A. Constants you need to change

COPYSCAPE_USERNAME = settings.COPYSCAPE_USERNAME
COPYSCAPE_API_KEY = settings.COPYSCAPE_API_KEY

COPYSCAPE_API_URL = "http://www.copyscape.com/api/"


# B. Functions for you to use (all accounts)

def copyscape_api_url_search_internet(url, full=0):
    return copyscape_api_url_search(url, full, 'csearch')

def copyscape_api_text_search_internet(text, encoding, full=0):
    return copyscape_api_text_search(text, encoding, full, 'csearch')

def copyscape_api_check_balance():
    return copyscape_api_call('balance')


# C. Functions for you to use (only accounts with private index enabled)

def copyscape_api_url_search_private(url, full=0):
    return copyscape_api_url_search(url, full, 'psearch')

def copyscape_api_url_search_internet_and_private(url, full=0):
    return copyscape_api_url_search(url, full, 'cpsearch')

def copyscape_api_text_search_private(text, encoding, full=0):
    return copyscape_api_text_search(text, encoding, full, 'psearch')

def copyscape_api_text_search_internet_and_private(text, encoding, full=0):
    return copyscape_api_text_search(text, encoding, full, 'cpsearch')

def copyscape_api_url_add_to_private(url, id=None):
    params={}
    params['q']=url
    if id is not None:
        params['i']=id
    
    return copyscape_api_call('pindexadd', params)

def copyscape_api_text_add_to_private(text, encoding, title=None, id=None):
    params={}
    params['e']=encoding
    if title is not None:
        params['a']=title
    if id != None:
        params['i']=id

    return copyscape_api_call('pindexadd', params, text)

def copyscape_api_delete_from_private(handle):
    params={}
    if handle is None:
        params['h'] = ''
    else: 
        params['h'] = handle
    
    return copyscape_api_call('pindexdel', params)


# D. Functions used internally

def copyscape_api_url_search(url, full=0, operation='csearch'):
    params={}
    params['q']=url
    params['c']=str(full)
    
    return copyscape_api_call(operation, params)

def copyscape_api_text_search(text, encoding, full=0, operation='csearch'):
    params={}
    params['e']=encoding
    params['c']=str(full)

    return copyscape_api_call(operation, params, text)

def copyscape_api_call(operation, params={}, postdata=None):
    urlparams={}
    urlparams['u'] = COPYSCAPE_USERNAME
    urlparams['k'] = COPYSCAPE_API_KEY
    urlparams['o'] = operation  
    urlparams.update(params)
    
    uri = COPYSCAPE_API_URL + '?'

    request = None
    if isPython2:
        uri += urllib.urlencode(urlparams)
        if postdata is None:
            request = urllib2.Request(uri)
        else:
            request = urllib2.Request(uri, postdata.encode("UTF-8"))
    else:
        uri += urllib.parse.urlencode(urlparams)
        if postdata is None:
            request = urllib.request.Request(uri) 
        else:
            request = urllib.request.Request(uri, postdata.encode("UTF-8"))
    
    try: 
        response = None
        response = urllib.request.urlopen(request)
        res = response.read()
        return CopyscapeTree.fromstring(res)    
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
        
    return None

def copyscape_title_wrap(title):
    return title+":"

def copyscape_node_wrap(element):
    return copyscape_node_recurse(element)

def copyscape_node_recurse(element, depth=0):
    ret = ""
    if element is None:
        return ret

    ret += "\t"*depth + " " + element.tag + ": "
    if element.text is not None:
        ret += element.text.strip()
    ret += "\n"
    for child in element:
        ret += copyscape_node_recurse(child,depth+1)
        
    return ret

    
#   E. Some examples of use

if 'COPYSCAPE_RUN_EXAMPLES' in globals() and COPYSCAPE_RUN_EXAMPLES:
    exampletext='We hold these truths to be self-evident, that all men are created equal, that they are endowed by their '+ \
        'Creator with certain unalienable rights, that among these are Life, Liberty, and the pursuit of Happiness. That to '+ \
        'secure these rights, Governments are instituted among Men, deriving their just powers from the consent of the '+ \
        'governed. That whenever any Form of Government becomes destructive of these ends, it is the Right of the People to '+ \
        'alter or to abolish it, and to institute new Government, laying its foundation on such principles and organizing '+ \
        'its powers in such form, as to them shall seem most likely to effect their Safety and Happiness. Prudence, indeed, '+ \
        'will dictate that Governments long established should not be changed for light and transient causes; and '+ \
        'accordingly all experience hath shown, that mankind are more disposed to suffer, while evils are sufferable, than '+ \
        'to right themselves by abolishing the forms to which they are accustomed. But when a long train of abuses and '+ \
        'usurpations, pursuing invariably the same Object evinces a design to reduce them under absolute Despotism, it is '+ \
        'their right, it is their duty, to throw off such Government, and to provide new Guards for their future security. '+ \
        'Such has been the patient sufferance of these Colonies; and such is now the necessity which constrains them to '+ \
        'alter their former Systems of Government. The history of the present King of Great Britain is a history of '+ \
        'repeated injuries and usurpations, all having in direct object the establishment of an absolute Tyranny over these '+ \
        'States. To prove this, let Facts be submitted to a candid world. He has refused his Assent to Laws, the most '+ \
        'wholesome and necessary for the public good. '+ \
        'We, therefore, the Representatives of the United States of America, in General Congress, Assembled, '+ \
        'appealing to the Supreme Judge of the world for the rectitude of our intentions, do, in the Name, and by Authority '+ \
        'of the good People of these Colonies, solemnly publish and declare, That these United Colonies are, and of Right '+ \
        'ought to be free and independent states; that they are Absolved from all Allegiance to the British Crown, and that '+ \
        'all political connection between them and the State of Great Britain, is and ought to be totally dissolved; and '+ \
        'that as Free and Independent States, they have full Power to levy War, conclude Peace, contract Alliances, '+ \
        'establish Commerce, and to do all other Acts and Things which Independent States may of right do. And for the '+ \
        'support of this Declaration, with a firm reliance on the Protection of Divine Providence, we mutually pledge to '+ \
        'each other our Lives, our Fortunes, and our sacred Honor.'

    print(copyscape_title_wrap('Response for a simple URL Internet search'))
    print(copyscape_node_wrap(copyscape_api_url_search_internet('http://www.copyscape.com/example.html')))

    print(copyscape_title_wrap('Response for a URL Internet search with full comparisons for the first two results'))
    print(copyscape_node_wrap(copyscape_api_url_search_internet('http://www.copyscape.com/example.html', 2)))

    print(copyscape_title_wrap('Response for a simple text Internet search'))
    print(copyscape_node_wrap(copyscape_api_text_search_internet(exampletext, "UTF-8")))

    print(copyscape_title_wrap('Response for a text Internet search with full comparisons for the first two results'))
    print(copyscape_node_wrap(copyscape_api_text_search_internet(exampletext, "UTF-8", 2)))

    print(copyscape_title_wrap('Response for a check balance request'))
    print(copyscape_node_wrap(copyscape_api_check_balance()))

    print(copyscape_title_wrap('Response for a URL add to private index request'))
    print(copyscape_node_wrap(copyscape_api_url_add_to_private('http://www.copyscape.com/example.html')))

    print(copyscape_title_wrap('Response for a text add to private index request'))
    response=copyscape_api_text_add_to_private(exampletext, "UTF-8", 'Extract from Declaration of Independence', 'EXAMPLE_1234')
    print(copyscape_node_wrap(response))

    handle = ''
    if response is not None and response.find('handle') is not None:
        handle = response.find('handle').text

    print(copyscape_title_wrap('Response for a URL private index search'))
    print(copyscape_node_wrap(copyscape_api_url_search_private('http://www.copyscape.com/example.html')))

    print(copyscape_title_wrap('Response for a delete from private index request'))
    print(copyscape_node_wrap(copyscape_api_delete_from_private(handle)))

    print(copyscape_title_wrap('Response for a text search of both Internet and private index with full comparisons for the first result (of each type)'))
    print(copyscape_node_wrap(copyscape_api_text_search_internet_and_private(exampletext, "UTF-8", 1)))
