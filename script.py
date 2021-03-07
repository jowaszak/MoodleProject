###########################################################################
#
#A script automation in Python for Moodle that allows adding lecture material links and links to
#individual class recordings into the correct module sections (weeks) on each run without duplications.
#
#Assuming that the script resides together with folders called wk1, wk2, wk3, ... wkX and in each folder
#there is an index.html (slides) file and wkX.pdf file that corresponds to a lecture given in class that
#week.
#
# At the moment the links to the file point to the source code , but once enable github page and you can 
# change the base url to https://{user}.github.io/{project} 
#  
# If there is saturday class the material and the recording will be added to the Moodle
# 
# Assuming there are max two recordingsa per week
# 
# Assuming the cours to run continusly over year and if the new semester comes it will continue the weeks number sequence
# 
# 
##########################################################################



# Import requred libriries 
from requests import get, post
import json
from datetime import datetime, date
import pandas as pd 
import numpy as np
import glob
from bs4 import BeautifulSoup
from urllib.request import urlopen
import re
import substring

# Module variables to connect to moodle api:
# Insert token and URL for your site here.
# Mind that the endpoint can start with "/moodle" depending on your installation.
KEY = "8cc87cf406775101c2df87b07b3a170d"
URL = "https://034f8a1dcb5c.eu.ngrok.io"
ENDPOINT = "/webservice/rest/server.php"

#URL base for links to the file 
# change the base url to https://{user}.github.io/{project} if needed, 
ENDPOINTFILES= 'https://github.com/jowaszak/MoodleProject/blob/master/'

#Recordings in Google drives
URLGOOGLE = "https://drive.google.com/drive/folders/1pFHUrmpLv9gEJsvJYKxMdISuQuQsd_qX"
PAGE = urlopen(URLGOOGLE)
HTML = PAGE.read().decode("utf-8")
SOUP = BeautifulSoup(HTML,"html.parser")

################################################
# Rest-Api classes Moodle
# 
# 
################################################

def rest_api_parameters(in_args, prefix='', out_dict=None):
    """Transform dictionary/array structure to a flat dictionary, with key names
    defining the structure.
    Example usage:
    >>> rest_api_parameters({'courses':[{'id':1,'name': 'course1'}]})
    {'courses[0][id]':1,
     'courses[0][name]':'course1'}
    """
    if out_dict == None:
        out_dict = {}
    if not type(in_args) in (list, dict):
        out_dict[prefix] = in_args
        return out_dict
    if prefix == '':
        prefix = prefix + '{0}'
    else:
        prefix = prefix + '[{0}]'
    if type(in_args) == list:
        for idx, item in enumerate(in_args):
            rest_api_parameters(item, prefix.format(idx), out_dict)
    elif type(in_args) == dict:
        for key, item in in_args.items():
            rest_api_parameters(item, prefix.format(key), out_dict)
    return out_dict


def call(fname, **kwargs):
    """Calls moodle API function with function name fname and keyword arguments.
    Example:
    >>> call_mdl_function('core_course_update_courses',
                           courses = [{'id': 1, 'fullname': 'My favorite course'}])
    """
    parameters = rest_api_parameters(kwargs)
    parameters.update(
        {"wstoken": KEY, 'moodlewsrestformat': 'json', "wsfunction": fname})
    # print(parameters)
    response = post(URL+ENDPOINT, data=parameters).json()
    if type(response) == dict and response.get('exception'):
        raise SystemError("Error calling Moodle API\n", response)
    return response




class LocalGetSections(object):
    """Get settings of sections. Requires courseid. Optional you can specify sections via number or id."""

    def __init__(self, cid, secnums=[], secids=[]):
        self.getsections = call('local_wsmanagesections_get_sections',
                                courseid=cid, sectionnumbers=secnums, sectionids=secids)


class LocalUpdateSections(object):
    """Updates sectionnames. Requires: courseid and an array with sectionnumbers and sectionnames"""

    def __init__(self, cid, sectionsdata):
        self.updatesections = call(
            'local_wsmanagesections_update_sections', courseid=cid, sections=sectionsdata)




#################################
###         Google Drive video links
### load to dataframe 
### get the links and identify which week it belongs to
#################################



#get the details of the videos which are under the class Q5txwe
recs = SOUP.find_all('div',class_ ='Q5txwe')

#extract out just the name of the videos into a dataframe
vids = pd.DataFrame(SOUP.find_all('div',class_ ='Q5txwe'))

vids.columns = ['FileName']
#print(vids)
columns = ['hashid']

ext = pd.DataFrame(columns=columns)

#extract the hashvalues of the videos into a dataframe
for rec in recs:
    id =rec.parent.parent.parent.parent.attrs['data-id']
    ext = ext.append({'hashid': id}, ignore_index=True)

#merge the two dataframes
dfGoogle = pd.merge(vids, ext, left_index=True, right_index=True)

#get the date
dfGoogle["video_date"] = dfGoogle['FileName'].str[:10]

#built the HTML  containing links
dfGoogle["Link"] = '''<a href="''' +"https://drive.google.com/file/d/"+dfGoogle['hashid'].astype(str)+  '''">Recorded session on : '''+ dfGoogle["video_date"].astype(str) + '</a><br>'


# Semester started week 40, it run to next year 2021 so it will reset to 1. 
# First the code extracts the week number then based on the value using pandas adds sectionnum that is the week number
#This column will be used to erge it to the final dataframe
dfGoogle['WeekNumber'] = pd.to_datetime(dfGoogle['video_date'],  format='%Y-%m-%d').dt.week

dfGoogle['sectionnum']= pd.np.where(dfGoogle['WeekNumber']>=40,
                        dfGoogle['WeekNumber']-39, 
                        dfGoogle['WeekNumber']+14
                        )

#pivot table to concat the the HTML if there is more then one recording per
dfGoogle['Group']= dfGoogle.groupby(dfGoogle['WeekNumber']).rank(method="first", ascending=True).astype(str)
dfGoogle= pd.pivot_table(dfGoogle, 
                          values = 'Link', 
                          index=['sectionnum'], 
                          columns = ['Group'],
                          aggfunc=lambda x: ' '.join(x)
                          ).reset_index()

# assuming there be only two recordings per week concat the two columns to get the links in one line
dfGoogle['summaryFile'] = dfGoogle['1.0'].astype(str)+dfGoogle['2.0'].astype(str)



#################################
###              Moodle 
### Get all sections of the course and load to the dataframe
###
#################################

courseid = "10"  # Exchange with valid id.
 

# Get all sections of the course.
sec = LocalGetSections(courseid)
# write data do dataframe
dfmoodle = pd.DataFrame(sec.getsections) 

## Get the title last date S after substring occurrence -  using partition()
## initializing split word 
#splChac = '-'
## Add column using partition() 
#dfmoodle['LastDate']= pd.np.where(dfmoodle['name'].str.contains(splChac),
#                      dfmoodle['name'].str.partition("-")[2] , ""
#                                  #substring.substringByChar(dfmoodle['name'], startChar=splChac)
#                        )
#print(dfmoodle)


#################################
###                 Files 
### Read the Subfolders and load to the dataframe
###
#################################+
# use Glob() function to find files recursively

files=[]
for file in glob.iglob('**/*\*.*', recursive=True):
    files.append(
            {
                    'FileName':file
            }
        )


#Load to DF

dfFiles= pd.DataFrame(files)


#Add column based on condition to know what file it is
conditions= [
    (dfFiles.FileName.str.endswith('.html')),
    (dfFiles.FileName.str.endswith('.md')),
    (dfFiles.FileName.str.endswith('.pdf'))
    ]

values=['html','md','pdf']

dfFiles['FileType'] = np.select(conditions, values)

#print(dfFiles)
# Exctract week number and add column
dfFiles['sectionnum'] = dfFiles.FileName.str.extract('(\d+)').astype(int)

#add HTML that should be in summary
dfFiles['HTML'] = '''<a href="''' + ENDPOINTFILES  + dfFiles['FileName'].astype(str)+ '''">Week'''+  dfFiles['sectionnum'].astype(str) + ': ' + dfFiles['FileName'].astype(str) + '</a><br>'


#pivot table to concat the values later
dfFiles= pd.pivot_table(dfFiles, 
                          values = 'HTML', 
                          index=['sectionnum'], 
                          columns = ['FileType'],
                          aggfunc=lambda x: ' '.join(x)
                          ).reset_index()

dfFiles['summaryFile'] = dfFiles['html'].astype(str)+dfFiles['pdf'].astype(str)



#Merge the two dataframes and 
dfmerge = pd.merge(dfFiles, dfmoodle[['summary','sectionnum']], on=['sectionnum'], how='left')
#add google recordings
dfmerge = pd.merge(dfGoogle, dfmerge, on=['sectionnum'], how='left')

#with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.max_colwidth', None):#

#    print(dfmerge)

#setting the index of data frame
#dfmerge.set_index("sectionnum", inplace=True)

#Lookup the sections to update

dfmerge['summaryFile']=dfmerge['summaryFile_y']+dfmerge['summaryFile_x']
dfmerge['summaryFile']= dfmerge['summaryFile'].str.replace('>nan','>')
#with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.max_colwidth', None):

#    print(dfmerge)
df = dfmerge.where(dfmerge['summary'] != dfmerge['summaryFile'])

#setting the index of data frame
#df.set_index("sectionnum", inplace=True)
#

#pd.options.display.float_format = '{:,.0f}'.format
with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.max_colwidth', None):
    print (df)

print(1)
print(dfmerge['summaryFile'].dropna())
print(2)
print(dfmerge['summaryFile'])
sectionsToUpdate= list(df['sectionnum'].dropna().astype(int))
print(sectionsToUpdate)

#df.info()
#print (sectionsToUpdate)






#################################
###
###
###
#################################
#Quick reset the sections to update
for sections in sectionsToUpdate:
    #  Assemble the payload
    data = [{'type': 'num', 'section': 0, 'summary': '', 'summaryformat': 1, 'visible': 1 , 'highlight': 0, 'sectionformatoptions': [{'name': 'level', 'value': '1'}]}]
    courseid = "10"  # Exchange with valid id.
    # Assemble the correct summary
    summary = ''
    #print(summary )
    # Assign the correct summary
    data[0]['summary'] = summary

    # Set the correct section number
    UpdateSection= sections
    data[0]['section'] = UpdateSection
  
    #print(data)
    # Write the data back to Moodle
    sec_write = LocalUpdateSections(courseid, data)

for sections in sectionsToUpdate:
    #  Assemble the payload
    data = [{'type': 'num', 'section': 0, 'summary': '', 'summaryformat': 1, 'visible': 1 , 'highlight': 0, 'sectionformatoptions': [{'name': 'level', 'value': '1'}]}]
    courseid = "10"  # Exchange with valid id.
    # Assemble the correct summary
    summary = df['summaryFile'].where(df['sectionnum']== sections).dropna()
    #print(summary )


    # Assign the correct summary
    data[0]['summary'] = summary

    # Set the correct section number
    UpdateSection= sections
    data[0]['section'] = UpdateSection
  
   # print(data)
    # Write the data back to Moodle
    sec_write = LocalUpdateSections(courseid, data)
