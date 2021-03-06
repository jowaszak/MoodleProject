from requests import get, post
import json
import datetime
import pandas as pd 
import numpy as np
import glob

# Module variables to connect to moodle api:
# Insert token and URL for your site here.
# Mind that the endpoint can start with "/moodle" depending on your installation.
KEY = "8cc87cf406775101c2df87b07b3a170d"
URL = "https://034f8a1dcb5c.eu.ngrok.io"
ENDPOINT = "/webservice/rest/server.php"
ENDPOINTFILES= 'https://github.com/jowaszak/MoodleProject/blob/master/'

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

################################################
# Rest-Api classes
################################################


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

################################################
# Example
################################################


courseid = "10"  # Exchange with valid id.
# Get all sections of the course.
sec = LocalGetSections(courseid)



# Get all sections of the course.
sec = LocalGetSections(courseid)
#print(sec.getsections)




#  Assemble the payload
#data = [{'type': 'num', 'section': 0, 'summary': '', 'summaryformat': 1, 'visible': 1 , 'highlight': 0, 'sectionformatoptions': [{'name': 'level', 'value': '1'}]}]

## Assemble the correct summary
#summary = '<a href="https://mikhail-cct.github.io/ca3-test/wk1/">Week 1: Introduction</a><br>'

## Assign the correct summary
#data[0]['summary'] = summary

## Set the correct section number
#data[0]['section'] = 1

## Write the data back to Moodle
#sec_write = LocalUpdateSections(courseid, data)


# write data do dataframe
dfmoodle = pd.DataFrame(sec.getsections) 

#print all
#with pd.option_context('display.max_rows', None, 'display.max_columns', None):
#    print (dfObj)


        #"availability",
        #"courseformat",
        #"id",
        #"name",
        #"sectionformatoptions",
        #"sectionnum",
        #"sequence",
        #"summary",
        #"summaryformat",
        #"uservisible",
        #"visible"

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

print(dfFiles)
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

dfFiles['summaryFile'] = dfFiles['html'].astype(str)+dfFiles['md'].astype(str)+dfFiles['pdf'].astype(str)



#Merge the two dataframes and 
dfmerge = pd.merge(dfFiles, dfmoodle[['summary','sectionnum']], on=['sectionnum'], how='left')

#setting the index of data frame
#dfmerge.set_index("sectionnum", inplace=True)

#Lookup the sections to update

df = dfmerge.where(dfmerge['summary'] != dfmerge['summaryFile']).dropna()

#setting the index of data frame
#df.set_index("sectionnum", inplace=True)
#

#pd.options.display.float_format = '{:,.0f}'.format
##with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.max_colwidth', None):
##    print (dfmerge['sectionnum'])
print(df)
sectionsToUpdate= list(df['sectionnum'].astype(int))
print(sectionsToUpdate)

#df.info()
#print (sectionsToUpdate)


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
  
    print(data)
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
  
    print(data)
    # Write the data back to Moodle
    sec_write = LocalUpdateSections(courseid, data)
