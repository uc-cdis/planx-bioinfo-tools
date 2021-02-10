from cdispyutils.hmac4 import get_auth
from scipy import stats
import statsmodels.api as sm
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.image as mpimg
from scipy.stats import ranksums
import pandas as pd
import numpy as np
import datetime
import requests
import glob
import json
import os
from utils import utils
from operator import add
from scipy.stats import expon
from pydoc import help
from scipy.stats.stats import pearsonr


summary_order = [
   "_study_count",
   "_case_count",
   "_demographic_count",
   "_diagnosis_count",
   "_mri_exam_count",
   "_mri_result_count"
]

summary_count_headers = {
    "_case_count": "Cases",
    "_study_count": "Studies",
    "_demographic_count": "Demographic records",
    "_diagnosis_count": "Diagnosis records",
    "_mri_exam_count": "MRI Parameters",
    "_mri_result_count": "MRI Results"
}

project_names = {
    "bhc-cnp-open-fmri": "Open FMRI",
    "bhc-fmri-duke-test": "Duke FMRI"
}

hemisphere_names = {
    "lh": "Left Hemisphere",
    "rh": "Right Hemisphere"
}

regions={
    'Amygdala':'Amyg',
    'Caudal':'Caud',
    'Hippocampus':'Hip',
    'Nucleus accumbens':'NAcc',
    'Pallidus ':'Pall',
    'Putamen':'Put',
    'Subcortical':'Subcortical',
    'Thalamus':'Thal'
}
hippo_subfields=['Hippocampal_tail','subiculum','CA1','hippocampal-fissure','presubiculum','parasubiculum','molecular_layer_HP','GC-ML-DG','CA3','CA4','fimbria','HATA']
color_list=['b', 'g', 'r', 'c', 'm', 'y', 'k','b','g','r','c','m']

api_url = 'https://data.braincommons.org/'

class DiseasesTable(dict):
    ''' Represent disease table in HTML format for visualization '''
 
    def _repr_html_(self):
        html = []
        html.append("<table style>")
        html.append("<thead>")  
        html.append("<th>Disease</th>")  
        html.append("<th># Subjects</th>")
        html.append("</thead>")
        total = 0
        for key in self:
            html.append("<tr>") 
            html.append("<td>%s</td>" % key)             
            html.append("<td>%s</td>" % self[key])           
            html.append("<tr>")
            total += self[key]
        html.append("<td>TOTAL</td>")             
        html.append("<td>%s</td>" % total)             
        html.append("</table>")        
        
        return ''.join(html)

class MetricsTable(dict):
    ''' Represent metrics tables in HTML format for visualization '''
 
    def _repr_html_(self):
        html = []
        html.append("<table style>")
        html.append("<thead>")  
        html.append("<th>Metric</th>")  
        html.append("<th>Value</th>")
        html.append("</thead>")       
        for key in self:
            html.append("<tr>") 
            html.append("<td>%s</td>" % key)             
            html.append("<td>%s</td>" % self[key])           
            html.append("<tr>") 
        html.append("</table>")        
        
        return ''.join(html)

class SummaryTable(dict):
    ''' Represent result tables in HTML format for visualization '''
 
    def _repr_html_(self):
        html = []
        html.append("<table style>")
        html.append("<thead>")  
        html.append("<th>Category</th>")  
        html.append("<th>Counts</th>")
        html.append("</thead>")       
        for key in summary_order:
            html.append("<tr>") 
            html.append("<td>%s</td>" % summary_count_headers[key])             
            html.append("<td>%s</td>" % self[key])           
            html.append("<tr>") 
        html.append("</table>")        
        
        return ''.join(html)

def add_keys(filename):
    ''' Get auth from our secret keys '''

    global auth 
    json_data=open(filename).read()
    keys = json.loads(json_data)
    auth = requests.post(api_url + 'user/credentials/cdis/access_token', json=keys)
    
def query_api(query_txt, variables = None):
    ''' Request results for a specific query '''

    if variables == None:
        query = {'query': query_txt}
    else:
        query = {'query': query_txt, 'variables': variables}        
    
    output = requests.post(api_url + 'api/v0/submission/graphql', headers={'Authorization': 'bearer '+ auth.json()['access_token']}, json=query).text
    data = json.loads(output)    
    
    if 'errors' in data:
        print(data)   
    
    return data 

def query_summary_counts(project_id):
    ''' Query summary counts for each data type'''

    query_txt = """query Counts ($projectID: [String]) {
                      _case_count(project_id: $projectID)   
                      _study_count(project_id: $projectID)
                      _demographic_count(project_id: $projectID)
                      _diagnosis_count(project_id: $projectID)
                      _mri_exam_count(project_id: $projectID)
                      _mri_result_count(project_id: $projectID)
               } """ 
    variables = { 'projectID': project_id }

    data = query_api(query_txt, variables) 
       
    table = SummaryTable(data['data'])
    
    return table

def query_summary_field(field, field_node, project_id = None):
    ''' Query summary counts for specific node'''
   
    if project_id != None:
        query_txt = """query { %s(first:0, project_id: "%s") {%s}} """ % (field_node, project_id, field) 
    else:
        query_txt = """query { %s(first:0) {%s project_id}} """ % (field_node, field)    
    
        
    data = query_api(query_txt)
    
    summary = {}
    total = []
    for d in data['data'][field_node]:
        
        if isinstance(d[field], float):
            d[field] = str(d[field])[:-2]        
        
        if 'project_id' in d:  
            summary.setdefault(d['project_id'], {})
            summary[d['project_id']].setdefault(d[field], 0)
            summary[d['project_id']][d[field]] += 1
            if d[field] not in total:
                total.append(d[field])            
        else:
            summary.setdefault(d[field], 0)        
            summary[d[field]] += 1
    
    if project_id != None:
        plot_field_metrics(summary, field)
    else:
        plot_overall_metrics(summary, field, total)        
    
    return summary

def plot_distribution(filename, measure, bins):
    
    
    pd = show_all_measures(filename)
    column = pd[measure]
        
    # the histogram of the data
    x=plt.figure(figsize=(8, 4))
    fig, ax = plt.subplots(1, 1)
    n, positions, patches = ax.hist(column, bins, facecolor='b', alpha=0.75)
        
    plt.xlabel(measure)
    plt.ylabel('Counts')
    plt.title('Histogram of ' + measure)
    plt.grid(True) 

def plot_boxplot(filename, measureL,measureR):
    
    
    pd = show_all_measures(filename)
    columnL = pd[measureL]
    columnR = pd[measureR]
        
    # the boxplot of the data
    plt.figure(figsize=(8, 8))
    fig, ax = plt.subplots()
    ax.boxplot([columnL,columnR])
        
    #plt.xlabel([measureL, measureR])
    ax.set_xticklabels([measureL, measureR])
    plt.ylabel('Value')
    plt.title('Boxplots of ' + measureL + ' and '+ measureR)
    plt.grid(True) 
    plt.show()
    
def scatter_all_hipp_subfield_vol(filename):
    pd=show_all_measures(filename)
    l=len(hippo_subfields)
    #figsize width 20, length 10*(int(l/2+0.5) ,because 2 fig every row
    fig = plt.figure(figsize= (10, 5*(int(l/2+0.5))))
    pos=0
    for i in hippo_subfields:       
        x=pd['L_'+i]
        y=pd['R_'+i]
        pos += 1                             
        a=fig.add_subplot(int(l/2+0.5),2,pos)
        #a.axis('off')                 
        a.set_title('left vs right '+i, fontsize=14)
        #plt.scatter(x, y, c="g", alpha=0.5, marker=r'$\clubsuit$',label="Luck")
        plt.scatter(x, y, c=color_list[pos-1], alpha=0.3)
        plt.xlabel(i+" of left")
        plt.ylabel(i+" of right")
        #plt.legend(loc=2)
    plt.tight_layout( w_pad=8, h_pad=8)
    plt.show() 
    
def scatter_one_hipp_subfield_corr(filename,sub_field):
    pd=show_all_measures(filename)

    #figsize width 20, length 10*(int(l/2+0.5) ,because 2 fig every row
    fig = plt.figure(figsize= (14, 14))
       
    x=pd['L_'+sub_field]
    y=pd['R_'+sub_field]
    pp_x=sm.ProbPlot(x,fit=True)
    pp_y=sm.ProbPlot(y,fit=True)
    corr=pearsonr(x, y)
    #test normal on left 
    a=fig.add_subplot(2,2,1)                     
    a.set_title('left '+sub_field +' vs normal Q-Q plot', fontsize=16)
    sm.graphics.qqplot(x,line='45',fit=True, ax=a)
    plt.ylabel("Left "+sub_field+" quantiles")

    
    #test normal on right
    a=fig.add_subplot(2,2,2)                     
    a.set_title('right '+sub_field +' vs normal Q-Q plot', fontsize=16)
    sm.graphics.qqplot(y,line='45',fit=True, ax=a)
    plt.ylabel("Right "+sub_field+" quantiles")
    
    a=fig.add_subplot(2,2,3)
        #a.axis('off')                 
    a.set_title('left vs right '+sub_field+' scatter plot', fontsize=16)
        #plt.scatter(x, y, c="g", alpha=0.5, marker=r'$\clubsuit$',label="Luck")
    lab="Pearson correlation: %f\np-value: %f" % (corr[0],corr[1])
    a.text(0.2,0.95,lab,horizontalalignment='center',
        verticalalignment='center',
        #rotation=45,
        transform=a.transAxes)
    plt.scatter(x, y, c='b', alpha=0.3)
    plt.xlabel(sub_field+" of left")
    plt.ylabel(sub_field+" of right")
    #plt.legend(loc=2)
    
    a=fig.add_subplot(2,2,4)                    
    a.set_title('left vs right '+sub_field +' Q-Q plot', fontsize=16)
    pp_x.qqplot(other=pp_y, line='45',ax=a)
    plt.xlabel("Quantiles of left "+sub_field)
    plt.ylabel("Quantiles of right "+sub_field)
    

 
    
    plt.tight_layout( w_pad=10, h_pad=10)
    plt.show()
    

def field_distribution(field, field_node, project_id, distrib=None, rate=None, bins = None):
    ''' Plot distribution for one field'''
   
    if project_id != None:
        query_txt = """query { %s(first:0, project_id: "%s") {%s}} """ % (field_node, project_id, field) 
    else:
        query_txt = """query { %s(first:0) {%s project_id}} """ % (field_node, field)    
    
        
    data = query_api(query_txt)
    
    data = query_api(query_txt)
    
    summary = {}
    total = []
    for d in data['data'][field_node]:
                
        if isinstance(d[field], float):
            d[field] = str(d[field])[:-2]        
        
        if 'project_id' in d:  
            summary.setdefault(d['project_id'], {})
            summary[d['project_id']].setdefault(d[field], 0)
            summary[d['project_id']][d[field]] += 1
            if d[field] not in total:
                total.append(d[field])            
        else:
            summary.setdefault(d[field], 0)        
            summary[d[field]] += 1    
         
    if len(summary)>10:
        
        accumulated = []
        for d in data['data'][field_node]:
            if d[field] != None:
                accumulated.append(float(d[field]))
        
        # the histogram of the data
        plt.figure(figsize=(8, 4))
        fig, ax = plt.subplots(1, 1)
        n, positions, patches = ax.hist(accumulated, bins, facecolor='b', alpha=0.75)
        total=len(accumulated)
        
        plt.xlabel(field)
        plt.ylabel('Counts')
        plt.title('Histogram of ' + field)
        plt.grid(True)
    
    else:
        
        N = len(summary)

        values = []
        types = []

        for n in sorted(summary, key=summary.get, reverse=True):
            values.append(summary[n])
            types.append(n)
            
        total = sum(values)
        positions = np.arange(N)
        fig, ax = plt.subplots(1, 1, figsize=(3*N, N))

        size_prop = (N/10) + 1
        ax.bar(positions, values, 0.2, align='center', alpha=0.4, color='b')
  
        plt.title('Summary counts by (' + field + ')', fontsize=10*size_prop)
        plt.ylabel('COUNTS', fontsize=10*size_prop)    
        plt.ylim(0, max(values)+5)
        plt.xlabel(field.upper(), fontsize=10*size_prop)  
        plt.xticks(positions, types, fontsize=10*size_prop)         
   
    # fit curve
    if distrib == 'exponential':
        fit_curve = expon.pdf(positions, 0, 1.0/rate)*total
        ax.plot(positions, fit_curve, 'r-', lw=2)
    if distrib == 'uniform':
        fit_curve = [total/float(len(positions))] * len(positions)
        ax.plot(positions, fit_curve, 'r-', lw=2)  

def get_disease_cohorts(project_id):
    ''' Query summary counts for each data type'''
   
    query_txt = """query{
                      diagnosis(first:0, project_id:"%s"){
                          primary_diagnosis
                      } 
               } """ % (project_id)

    data = query_api(query_txt) 

    diagnosis_counts = {}
    for diagnosis in data['data']['diagnosis']:
        diagnosis_counts.setdefault(diagnosis['primary_diagnosis'], 0)
        diagnosis_counts[diagnosis['primary_diagnosis']] += 1    
    
    table = DiseasesTable(diagnosis_counts)
    
    return table
    
def plot_field_metrics(summary_counts, field):
    ''' Plot summary results in a barplot ''' 
    
    N = len(summary_counts)

    values = []
    types = []

    for n in sorted(summary_counts, key=summary_counts.get, reverse=True):
        values.append(summary_counts[n])
        types.append(n)
        
    positions = np.arange(N)        
    plt.figure(figsize=(3*N, N))   
    
    size_prop = (N/10) + 1
    plt.bar(positions, values, 0.2, align='center', alpha=0.4, color='b')
    plt.title('Summary counts by (' + field + ')', fontsize=10*size_prop)
    plt.ylabel('COUNTS', fontsize=10*size_prop)    
    plt.ylim(0, max(values)+5)
    plt.xlabel(field.upper(), fontsize=10*size_prop)  
    plt.xticks(positions, types, fontsize=10*size_prop)    
    
    for i, v in enumerate(values):
        plt.text(i, v, str(v), color='red', fontweight='bold', fontsize=10*size_prop)
    
   
    plt.show()
    

def plot_overall_metrics(summary_counts, field, totals):    
    ''' Visualize summary results across projects in a barplot ''' 
    
    results = {}
    projects = {}
    for project in summary_counts:
        
        results[project] = []
        projects.setdefault(project, 0)
            
        for value in totals:
            if value in summary_counts[project]:
                results[project].append(summary_counts[project][value])
                projects[project] += summary_counts[project][value]
            else:
                results[project].append(0)

    N = len(totals)
    positions = np.arange(N) 
    sorted_projects = sorted(projects, key=projects.get, reverse=True)
    bar_size = 0.2
    size_prop = (N/10) + 1
    
    plots = []
    plt.figure(figsize=(8, 4))
    left = [0]*N
    for pr in sorted_projects:
        p = plt.barh(positions, results[pr], bar_size, left, align='center', alpha=1)        
        plots.append(p[0])
        left = map(add, left, results[pr])
        
    plt.title('Summary counts by (' + field + ')', fontsize=10*size_prop)
    plt.xlabel('COUNTS', fontsize=10*size_prop)    
    plt.xlim(0, max(left)+5)
    plt.ylabel(field.upper(), fontsize=10*size_prop)  
    plt.yticks(positions, totals, fontsize=10*size_prop)    
    plt.legend(plots, sorted_projects, fontsize=10*size_prop)
           
    plt.show()     
    
    
def plot_measure_by_disease(results, title, measure, pvalues):
    ''' Visualize metrics from cortical pipeline per disease'''
    
    N = len(results)
    positions = np.arange(N) + 1    
    
    plt.figure()
    plt.boxplot(list(results.values()), patch_artist=True)
    plt.xticks(positions, results.keys(), rotation='vertical')
    plt.title(title + ' - ' + measure, fontsize = 16)
    plt.ylabel(measure) 
    bottom,top = plt.ylim()
    plt.ylim(bottom,top*1.05)
    
    for p, disease in zip(positions, pvalues):
        if pvalues[disease] > 0:
            col = "red"
            if pvalues[disease] < 0.01: col = "green" 
            plt.text(p, top, "p={0:.4f}".format(pvalues[disease]),
                 horizontalalignment='center', color=col, weight="bold")    
    
    plt.show()    

def read_result_file(file):
    ''' Read TSV/CSV files from MRI results'''    

    if '.tsv' in file:
        sep = '\t'
    elif '.csv' in file:
        sep = ','
    
    headers = []
    results = {}
    with open(file, mode='r') as infile:
        for line in infile:
            columns = line.strip('\n').split(sep)
            if not headers:
                headers = columns
            else:
                pos = 0
                for h in headers:
                    results[h] = columns[pos]
                    pos += 1
    
    return results    
    
    
def get_external_surface_qc(project_id, subject_id):       
    ''' Get external surface results from data model'''    
        
    # Query data
    query_txt = """query {
                      case(submitter_id: "%s"){
                        mri_exams(first:0){
                          mri_images(first:0){
                            mri_analysis_workflows(first:0){
                              mri_results(first:0, data_category: "MRI Derived Image", data_type: "Cortical Thickness"){
                                file_name
                              }
                            }
                          }
                        }
                      }
                }""" % (subject_id)
    
    data = query_api(query_txt)

    # Display external surface
    fig = plt.figure(figsize=(15, 15))
    fig.suptitle('EXTERNAL SURFACE SEGMENTATION', fontsize=20, fontweight='bold')    
    for file in data['data']['case'][0]['mri_exams'][0]['mri_images'][0]['mri_analysis_workflows'][0]['mri_results']:
        
        # Download image files if not in local
        image = './results/' + project_id + '/' + file['file_name']
        if not os.path.exists(image):
            image = utils.get_file_from_s3(file['file_name'], project_id)  
        
        # Plot images
        print image
        if 'lh.lat.' in image:
            title_view = 'Lateral View - Left Hemisphere'
            pos = 1
        elif 'lh.med.' in image:
            title_view = 'Medial View - Left Hemisphere'
            pos = 2                
        elif 'rh.lat.' in image:
            title_view = 'Lateral View - Right Hemisphere'
            pos = 3 
        elif 'rh.med.' in image:
            title_view = 'Medial View - Right Hemisphere'
            pos = 4                 
                
        a=fig.add_subplot(2,2,pos)
        a.axis('off')
        img = mpimg.imread(image)
        imgplot = plt.imshow(img)                  
        a.set_title(title_view, fontsize=18)        


def get_hippocampal_qc(project_id, subject_id, output_path, view, hemisphere):       
    ''' Get external surface results from data model'''    
       
    # Display external surface
    fig = plt.figure(figsize=(15, 15))
    fig.suptitle('HIPPOCAMPAL SEGMENTATION', fontsize=20, fontweight='bold')    
    pos = 0
    slides = ['20','40','60','80']
    for file in output_path:
        if view in file and hemisphere in file and not 'T1' in file and not '_fis' in file:
            print file
            title_view = '%s View (%s, slide %s)' % (view, hemisphere, slides[pos])
            pos += 1               
                
            a=fig.add_subplot(2,2,pos)
            a.axis('off')
            img = mpimg.imread(file)
            imgplot = plt.imshow(img)                  
            a.set_title(title_view, fontsize=18) 
            
def get_subcortical_qc(output_QC,reg_name,view):
    reg_name=regions[reg_name]
    f_list=[]
    for file in output_QC:
        if view in file and reg_name in file :
            f_list.append(file)
    l=len(f_list)    
    fig = plt.figure(figsize= (20, 10*(int(l/2.0+0.5))))
    #fig = plt.figure((4,4))
    
    #fig.suptitle('SUBCORTICAL SEGMENTATION', fontsize=20, fontweight='bold')    
    pos = 0
    for file in f_list:
            # get file name from the file path
            indicesB = [i for i, x in enumerate(file) if x == '/']
            indicesE = [i for i, x in enumerate(file) if x == '.']
            pic_title=file[(indicesB[-1]+1):indicesE[-1]]
            pos += 1                             
            a=fig.add_subplot(int(l/2.0+0.5),2,pos)
            a.axis('off')
            img = mpimg.imread(file)
            imgplot = plt.imshow(img)                  
            a.set_title(pic_title, fontsize=18) 
    plt.show()
   
def get_hippo_subfield_qc(output_QC,fiss_only,T1_only,view):
    f_list={}
    if fiss_only=='yes' and T1_only=='yes':
        print "fiss_only and T1_only can't be 'yes' simultaneously"
    if fiss_only=='yes' and T1_only=='no':
        for file in output_QC:
            if view in file and 'fis'in file:
                if 'left' in file:
                    f_list[file[-6:-4]+'left']=file
                else:
                    f_list[file[-6:-4]+'right']=file
    if fiss_only=='no' and T1_only=='yes':
        for file in output_QC:
            if view in file and 'T1'in file:
                if 'left' in file:
                    f_list[file[-6:-4]+'left']=file
                else:
                    f_list[file[-6:-4]+'right']=file
    if fiss_only=='no' and T1_only=='no':
        for file in output_QC:
            if view in file and not('fis'in file) and not('T1'in file):
                if 'left' in file:
                    f_list[file[-6:-4]+'left']=file
                else:
                    f_list[file[-6:-4]+'right']=file
        f_list['90abc']='/home/ubuntu/enigma/figures/Hippocampal_subfields_color_legend.png'
    
    l=len(f_list)    
    fig = plt.figure(figsize= (20, 10*(int(l/2.0+0.5))))
    #fig = plt.figure((4,4))
    
    #fig.suptitle('SUBCORTICAL SEGMENTATION', fontsize=20, fontweight='bold')   
    pos = 0
    for key in sorted(f_list.iterkeys()):
    #for file in f_list:
            # get file name from the file path
            indicesB = [i for i, x in enumerate(f_list[key]) if x == '/']
            indicesE = [i for i, x in enumerate(f_list[key]) if x == '.']
            pic_title=f_list[key][(indicesB[-1]+1):indicesE[-1]]
            pos += 1 
            a=fig.add_subplot(int(l/2.0+0.5),2,pos)
            a.axis('off')
            img = mpimg.imread(f_list[key])
            imgplot = plt.imshow(img)                  
            a.set_title(pic_title, fontsize=18) 
    plt.show()
        
def run_statistical_test(values):

    pvalues = {}
    for disease in values:
        if disease != 'Healthy':
            test = ranksums(values['Healthy'], values[disease])
            pvalues[disease] = test.pvalue    
        else:
            pvalues[disease] = -1
    
    return pvalues
        
def get_cortical_measure_by_disease(project_id, measure):
    ''' Query metrics from cortical pipeline'''
   
    query_txt = """query {
                      case(first:0, project_id: "%s"){
                        diagnoses(first:0){
                             primary_diagnosis
                        }
                        mri_exams(first:0){
                          mri_images(first:0){
                            mri_analysis_workflows(first:0){
                              mri_results(first:0, data_category: "MRI Derived Measures", data_type: "Cortical Thickness"){
                                file_name
                              }
                            }
                          }
                        }
                      }
                }""" % (project_id)
    
    data = query_api(query_txt)
    
    values = {}
    for case in data['data']['case']:
        if case['diagnoses']:
            diagnosis = case['diagnoses'][0]['primary_diagnosis']
            values.setdefault(diagnosis, [])
            if case['mri_exams'] \
               and case['mri_exams'][0]['mri_images'] \
               and case['mri_exams'][0]['mri_images'][0]['mri_analysis_workflows'] \
               and case['mri_exams'][0]['mri_images'][0]['mri_analysis_workflows'][0]['mri_results']:
                    resFile = case['mri_exams'][0]['mri_images'][0]['mri_analysis_workflows'][0]['mri_results'][0]['file_name']     
                    resFile = utils.get_file_from_s3(resFile, project_id)          
                    results = read_result_file(resFile)
                    if measure in results:
                        values[diagnosis].append(float(results[measure]))
    
    pvalues = run_statistical_test(values)
    
    plot_measure_by_disease(values, 'CORTICAL MEASUREMENTS', measure, pvalues)
    
    return values


def run_freesurfer(project_id, subject_id, mri_type = "T1-weighted"):
    ''' Run FreeSurfer for ENIGMA cortical pipeline'''

    # Query data
    query_txt = """query {
                      case(project_id: "%s", submitter_id: "%s"){
                         mri_exams(scan_type: "%s"){
                            mri_images{   
                               file_name
                            }
                         }
                      }
                }""" % (project_id, subject_id, mri_type)
    
    data = query_api(query_txt)

    # Get file from S3
    filename = data['data']["case"][0]['mri_exams'][0]['mri_images'][0]['file_name']
    localpath = utils.get_file_from_s3(filename, project_id)
    inputPath=(localpath[2:]).encode("ascii")
    #print type( inputPath)
    # Run freesurfer
    datetime_start = datetime.datetime.now()
    print "%s: Running FreeSurfer for %s subject..." % (str(datetime_start),subject_id)
    local_output = '/freesurfer/' + subject_id

    if not os.path.exists(local_output):
        #cmd = ['/bin/bash', 'run_freesurfer.sh', subject_id, localpath]
        cmd = ['sudo', 'docker', 'run', '--rm', '-i', '-v', '/home/ubuntu/demo:/input', '-v', '/home/ubuntu/demo'+local_output+':/opt/freesurfer/subjects', 'vistalab/freesurfer', 'recon-all', '-i', '/input/'+inputPath, '-subjid','70089', '-sd', '/input/freesurfer', '-all', '-openmp', '8']
        output = utils.run_command(cmd)
        datetime_end = datetime.datetime.now()
        print "%s: FreeSurfer FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        running_time = "07:10:52.3243"
        print "%s: FreeSurfer results were already found for %s subject." % (str(datetime_start), subject_id)
        print "%s: Running took %s." % (str(datetime_start), running_time)

def dowload_mri_image(project_id, subject_id, mri_type = "T1-weighted"):
    ''' Run FreeSurfer for ENIGMA cortical pipeline'''
    #mri_type:"T1-weighted" for hippo_sub and subcortical volume and "Resting fMRI" for resting pipeline. The other possible types:T2-weighted, Task-based fMRI and Diffusion-weighted (DTI)
    # Query data
    query_txt = """query {
                      case(project_id: "%s", submitter_id: "%s"){
                         mri_exams(scan_type: "%s"){
                            mri_images{
                               id
                               file_name
                            }
                         }
                      }
                }""" % (project_id, subject_id, mri_type)
    
    data = query_api(query_txt)
    # Get file from S3
    filename = data['data']["case"][0]['mri_exams'][0]['mri_images'][0]['file_name']
    fileid =  data['data']["case"][0]['mri_exams'][0]['mri_images'][0]['id']
    
    #localpath = utils.get_file_from_s3(filename, project_id)
    localpath = './results/' + project_id + '/' + filename
    response = utils.download_file(auth, api_url, fileid, localpath)
    inputPath=(localpath[2:]).encode("ascii")
    print  (inputPath)
    return inputPath
        
def run_freesurfer_test(project_id, subject_id, mri_type = "T1-weighted"):
    ''' Run FreeSurfer for ENIGMA cortical pipeline'''

    # Query data
    query_txt = """query {
                      case(project_id: "%s", submitter_id: "%s"){
                         mri_exams(scan_type: "%s"){
                            mri_images{
                               id
                               file_name
                            }
                         }
                      }
                }""" % (project_id, subject_id, mri_type)
    
    data = query_api(query_txt)
    # Get file from S3
    filename = data['data']["case"][0]['mri_exams'][0]['mri_images'][0]['file_name']
    fileid =  data['data']["case"][0]['mri_exams'][0]['mri_images'][0]['id']
    
    #localpath = utils.get_file_from_s3(filename, project_id)
    localpath = './results/' + project_id + '/' + filename
    response = utils.download_file(auth, api_url, fileid, localpath)
    inputPath=(localpath[2:]).encode("ascii")
    print  (inputPath)
    # Run freesurfer
    datetime_start = datetime.datetime.now()
    print "%s: Running FreeSurfer for %s subject..." % (str(datetime_start),subject_id)
    local_output = '/output/' + subject_id
    #if not os.path.exists(local_output):
        #os.mkdir('/home/ubuntu/enigma'+local_output)
    #cmd = ['sudo', 'docker', 'run', '--rm', '-i', '-v', '/home/ubuntu/enigma/figures:/input', '-v', '/home/ubuntu/enigma'+local_output+':/opt/freesurfer/subjects', 'vistalab/freesurfer', 'recon-all', '-i', '/input/'+inputPath, '-subjid','70089', '-all', '-openmp', '8']
    #output = utils.run_command(cmd)
    #datetime_end = datetime.datetime.now()
    #print "%s: FreeSurfer FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))


def extract_cortical_measures(project_id, subject_id):
    ''' Run Cortical Measures Extraction for ENIGMA cortical pipeline'''
    
    subject_path = './freesurfer'
    local_output = subject_path + '/' + subject_id
    datetime_start = datetime.datetime.now()
    
    # Run Cortical measures extraction
    if not os.path.exists(local_output):
        print "%s: ERROR: Didn't find FreeSurfer output for %s subject. Please run run_freesurfer function first."  (datetime_start,subject_id)
    else:
        
        print "%s: Extracting cortical measures for %s subject..." % (str(datetime_start), subject_id)        
        output_file = './results/' + project_id + '/cort_' + subject_id + '.csv' 
        
        cmd = ['/bin/bash', 'extract.sh', subject_id, subject_path, output_file]
        output = utils.run_command(cmd)
        
        datetime_end = datetime.datetime.now()
        print "%s: Extraction FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 

    return output_file


def run_external_segmentation(project_id, subject_id):
    ''' Run External Surface Segmentation from ENIGMA cortical pipeline'''    

    local_fs = './freesurfer/' + subject_id
    output_path = './results/' + project_id
    current_files = glob.glob(output_path + '/' + subject_id + '*.tif')
    datetime_start = datetime.datetime.now()  
    
    # Run segmentation
    if not os.path.exists(local_fs):
        print "%s: ERROR: Didn't find FreeSurfer output for %s subject. Please run run_freesurfer function first."  (datetime_start,subject_id)
    else:
        
        print "%s: Getting External Surface Segmentation for %s subject..." % (str(datetime_start), subject_id)         
        if len(current_files) > 1:
            datetime_end = datetime.datetime.now()    
            print "%s: External Surface Segmentation was already obtained for %s subject." % (str(datetime_end),subject_id)        
        else:
             
            cmd = ['/bin/bash', 'fsqc.sh', subject_id, output_path]
            output = utils.run_command(cmd)
        
            datetime_end = datetime.datetime.now()
            print "%s: Segmentation FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 

        datetime_plot = str(datetime.datetime.now())       
        print "%s: Visualizing results:" % (datetime_plot) 
        get_external_surface_qc(project_id, subject_id)

def run_hippocampal_segmentation(project_id, subject_id, view, hemisphere):
    ''' Run External Surface Segmentation from ENIGMA cortical pipeline'''    

    local_fs = './freesurfer/' + subject_id
    output_path = './freesurfer/QC'
    current_files = glob.glob(output_path + '/' + subject_id + '/*.png')
    datetime_start = datetime.datetime.now()  
    
    # Run segmentation
    if not os.path.exists(local_fs):
        print "%s: ERROR: Didn't find FreeSurfer output for %s subject. Please run run_freesurfer function first."  (datetime_start,subject_id)
    else:
        
        print "%s: Getting External Surface Segmentation for %s subject..." % (str(datetime_start), subject_id)         
        if len(current_files) > 1:
            datetime_end = datetime.datetime.now()    
            print "%s: External Surface Segmentation was already obtained for %s subject." % (str(datetime_end),subject_id)        
        else:
             
            cmd = ['/bin/bash', 'QC_subfields_step_1_prepare_extension.sh', subject_id, output_path]
            output = utils.run_command(cmd)
            cmd = ['octave-cli', '/NIfTI/QC_subfields_step_2_prepare_extension']
            output = utils.run_command(cmd)
        
            datetime_end = datetime.datetime.now()
            print "%s: Segmentation FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 

        datetime_plot = str(datetime.datetime.now())       
        print "%s: Visualizing results:" % (datetime_plot) 
        get_hippocampal_qc(project_id, subject_id, current_files, view, hemisphere)        
        

def show_all_measures(filename, metrics = None):
    ''' Display values for all subjects'''
        
    df = pd.read_csv(filename)    
    
    return df
            
        
        
def show_measures(filename, metrics = None):
    ''' Display values for a list of extracted measures '''
    
    results = read_result_file(filename)
    
    if metrics == None:
        metrics = results.keys()
    
    subset = {}
    for m in metrics:
        if m in results:
            subset[m] = results[m]
        else:
            current_dt = str(datetime.datetime.now())        
            print "%s: Unknown \"%s\" metric. Skipping it from visualization." % (current_dt, m)
            
    table = MetricsTable(subset)
    
    return table

def run_freesurfer_hippocampal(project_id, subject_id, mri_type = "T1-weighted"):
    ''' Run FreeSurfer for ENIGMA Hippocampal pipeline'''

    # Query data    
    query_txt = """query {
                      case(project_id: "%s", submitter_id: "%s"){
                         mri_exams(scan_type: "%s"){
                            mri_images{   
                               file_name
                            }
                         }
                      }
                }""" % (project_id, subject_id, mri_type)    
    
    data = query_api(query_txt)

    # Get file from S3
    filename = data['data']["case"][0]['mri_exams'][0]['mri_images'][0]['file_name']
    localpath = utils.get_file_from_s3(filename, project_id)
    
    # Run freesurfer
    datetime_start = datetime.datetime.now()
    print "%s: Running FreeSurfer for %s subject..." % (str(datetime_start),subject_id)
    local_output = './freesurfer/' + subject_id
    if not os.path.exists(local_output):
        cmd = ['/bin/bash', 'run_freesurfer_hippocampal.sh', subject_id]
        output = utils.run_command(cmd)
        datetime_end = datetime.datetime.now()
        print "%s: Hippocampal FreeSurfer FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "%s: Hippocampal FreeSurfer results were already found for %s subject." % (str(datetime_start), subject_id)
    
    

def extract_hippocampal_measures(project_id, subject_id):
    ''' Run Hippocampal Measures Extraction for ENIGMA Hippocampal pipeline'''
    
    subject_path = './freesurfer'
    local_output = subject_path + '/' + subject_id
    datetime_start = datetime.datetime.now()
    
    # Run Hippocampal measures extraction
    if not os.path.exists(local_output):
        print "%s: ERROR: Didn't find FreeSurfer output for %s subject. Please run run_freesurfer function first."  (datetime_start,subject_id)
    else:
        
        print "%s: Extracting hippocampal measures for %s subject..." % (str(datetime_start), subject_id)        
        output_file = './results/' + project_id + '/hippo_' + subject_id + '.csv' 
        
        cmd = ['/bin/bash', 'extract_subfields.sh', subject_id, subject_path, output_file]
        output = utils.run_command(cmd)
        
        datetime_end = datetime.datetime.now()
        print "%s: Extraction FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 

    return output_file

def extract_subcortical_measures(freesurfer_output_dir, output_file_name):
    ''' Run Subcortical Measures Extraction for ENIGMA Subcortical Pipeline'''
    
    output_file_name=freesurfer_output_dir+'/'+output_file_name+'.csv'
    
    datetime_start = datetime.datetime.now()
    
    # Run subcortical measures extraction

        
    print "%s: Extracting subcortical measures for input subjects..." % (str(datetime_start))        
    
        
    cmd = ['/bin/bash', '/home/ubuntu/enigma/output/extract_subcortical.sh', freesurfer_output_dir,output_file_name]
    output = utils.run_command(cmd)
        
    datetime_end = datetime.datetime.now()
    print "%s: Extraction FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 

    return output_file_name
    
def ENIGMA_subcortical_plots(extracted_data):
    '''Generating Histogram Plots for Subcortical Measures'''
    cmd = ['Rscript', '--no-save', '--slave', '--vanilla', '/home/ubuntu/enigma/figures/ENIGMA_plots.R',extracted_data]
    output = utils.run_command(cmd)
    #show histogram plots
    
    return

def detect_subcortical_outlier(extracted_info, visual):
    '''Detecting outlier(s) based on the extracted subcortical information'''
    datetime_start = datetime.datetime.now()
    print "%s: Detecting outlier(s) " % (str(datetime_start)) 
    cmd = ['/bin/bash', 'mkIQIrange.sh']
    outInfor = utils.run_command(cmd)
    n=outInfor.count("\n")
    print "%d Outliers detected:" % (n)
    print outInfor
    
    #cmd = ['/bin/bash', '/home/ubuntu/enigma/figures/detectOutlier.sh', '/home/ubuntu/enigma/output',extracted_info,'/home/ubuntu/enigma/figures']
    #output=utils.run_command(cmd)
    if visual.lower()=='yes':       
        print "Visualizing outlier(s)"
        cmd = ['/bin/bash', 'detectOutlier.sh']
        output=utils.run_command(cmd) 
        datetime_end = datetime.datetime.now()
        print "%s: Outlier detection and Visualization FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        datetime_end = datetime.datetime.now()
        print "%s: Outlier detection FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 

    return 
    


def subcortical_segmentationQC(subject_id, output_dir,reg,view):
# for demo: output_dir='/home/ubuntu/enigma/output/QC'
    output_dir=output_dir+'/'+subject_id      
    datetime_start = datetime.datetime.now()
    if not os.path.exists(output_dir):
        print "%s: Getting Subcortical Segmentation for %s subject..." % (str(datetime_start), subject_id)    
        cmd = ['docker', 'run', '-i', '-t', '--rm', '--name', 'octavecli', '-v', '$HOME:$HOME', '--user', '$UID:$GID', 'simexp/octave:3.8.1', '/bin/bash', '-c', '"export HOME=$HOME; cd $HOME; source /opt/minc-itk4/minc-toolkit-config.sh; octave /home/ubuntu/enigma/ENIGMA_QC/script_make_subcorticalFS_ENIGMA_QC.m"', subject_id, output_dir]
        output = utils.run_command(cmd)    
        datetime_end = datetime.datetime.now()
        print "%s: Segmentation FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "Subcortical segmentation already found"
        
    datetime_plot = str(datetime.datetime.now())     
    
    current_files = glob.glob(output_dir + '/*.png') 
    print "%s: Visualizing results" % (datetime_plot) 
    get_subcortical_qc(current_files,reg,view)
   
    return

def run_hippocampal_subfield_segmentation(subject_list):
    ''' Run FreeSurfer Hippocampal subfield segmentation'''

    # Query data    
   # query_txt = """query {
    #                  case(project_id: "%s", submitter_id: "%s"){
     #                    mri_exams(scan_type: "%s"){
      #                      mri_images{   
       #                        file_name
        #                    }
         #                }
          #            }
           #     }""" % (project_id, subject_id, mri_type)    
    
   # data = query_api(query_txt)

    # Get file from S3
    #filename = data['data']["case"][0]['mri_exams'][0]['mri_images'][0]['file_name']
    #localpath = utils.get_file_from_s3(filename, project_id)
    
    # Run freesurfer
    datetime_start = datetime.datetime.now()
    #print "%s: Running FreeSurfer for %s subject..." % (str(datetime_start),subject_id)
    #local_output = './freesurfer/' + subject_id
    if not os.path.exists("/home/ubuntu/enigma/output"):
        cmd = ['/bin/bash', '/home/ubuntu/demo/run_freesurfer_hippocampal_onListSub.sh', subject_list]
        output = utils.run_command(cmd)
        datetime_end = datetime.datetime.now()
        print "%s: Hippocampal FreeSurfer FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "%s: Hippocampal subfield segmentation results were already found for 26 subjects." % (str(datetime_start))
       
def extract_hippocampal_subfield_measures(freesurfer_output_dir, output_file_name):
    ''' Run Hippocampal Subfield Measures Extraction for ENIGMA Hippocampal Subfields Pipeline'''
    
    output_file_name=freesurfer_output_dir+'/'+output_file_name+'.csv'
    
    datetime_start = datetime.datetime.now()
    
    # Run subcortical measures extraction

        
    print "%s: Extracting hippocampal subfield measures for input subjects..." % (str(datetime_start))        
    
        
    cmd = ['/bin/bash', '/home/ubuntu/enigma/output/extract_subfields.sh', freesurfer_output_dir,output_file_name]
    output = utils.run_command(cmd)
        
    datetime_end = datetime.datetime.now()
    print "%s: Extraction FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 

    return output_file_name

def detect_outlier_hippo_subfields(extracted_info):
    '''Detecting outlier(s) based on the extracted subcortical information'''
    datetime_start = datetime.datetime.now()
    print "%s: Detecting outlier(s) " % (str(datetime_start)) 
    cmd = ['/bin/bash' ,'/home/ubuntu/enigma/output/detect_outlier_hippo_sub.sh']
    utils.run_command(cmd)
    with open('/home/ubuntu/enigma/output/QC_support.log', 'r') as content_file:
        content = content_file.read()
    #n=outInfor.count("\n")
    #print "%d Outliers detected:" % (n)
    print content
    datetime_end = datetime.datetime.now()
    print "%s: Outlier detection FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start)) 
    #cmd = ['/bin/bash', '/home/ubuntu/enigma/figures/detectOutlier.sh', '/home/ubuntu/enigma/output',extracted_info,'/home/ubuntu/enigma/figures']
    #output=utils.run_command(cmd)

def freeview_hippo_subSeg(subject):      
    cmd = ['/bin/bash', '/home/ubuntu/enigma/figures/freeview.sh',subject]
    output=utils.run_command(cmd)
    print "Visualization FINISHED" 
    return 

def hippo_subfield_segmentationQC(subject_id, output_dir,fiss_only,T1_only,view):
# for demo: output_dir='/home/ubuntu/enigma/output/QC'
    output_dir=output_dir+'/'+subject_id      
    datetime_start = datetime.datetime.now()
    if not os.path.exists(output_dir):
        print "%s: Getting Hippocampal Subfield Segmentation for %s subject..." % (str(datetime_start), subject_id)    
       # cmd = ['docker', 'run', '-i', '-t', '--rm', '--name', 'octavecli', '-v', '$HOME:$HOME', '--user', '$UID:$GID', 'simexp/octave:3.8.1', '/bin/bash', '-c', '"export HOME=$HOME; cd $HOME; source /opt/minc-itk4/minc-toolkit-config.sh; octave /home/ubuntu/enigma/ENIGMA_QC/script_make_subcorticalFS_ENIGMA_QC.m"', subject_id, output_dir]
       # output = utils.run_command(cmd)    
        datetime_end = datetime.datetime.now()
        print "%s: Segmentation FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "Hippocampal subfield segmentation already found"
        
    datetime_plot = str(datetime.datetime.now())     
    
    current_files = glob.glob(output_dir + '/*.png') 
    print "%s: Visualizing results" % (datetime_plot) 
    get_hippo_subfield_qc(current_files,fiss_only,T1_only,view)
   
    return

# for resting pipeline

def motion_correction(subject_id):
    if not os.path.exists('/mnt/subjectDir/sub-10159/func/nt_mc_RS.nii.gz'):
        print "%s: Running motion correction for %s subject..." % (str(datetime_start), subject_id)    
        cmd = ['/bin/bash', '/mnt/motion_correction.sh']
        output=utils.run_command(cmd)   
        datetime_end = datetime.datetime.now()
        print "%s: motion correction FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "Result of motion correction already found"
    
    return 

def calculate_tSNR(output_dir):
    if not os.path.exists('/mnt/subjectDir/sub-10159/func/nt_mc_RS.nii.gz'):
        print "%s: Calculating tSNR for %s subject..." % (str(datetime_start), subject_id)    
        cmd = ['/bin/bash', '/mnt/motion_correction.sh']
        output=utils.run_command(cmd)   
        datetime_end = datetime.datetime.now()
        print "%s: tSNR calculation FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "tSNR map already found"
    
    return

def brain_extraction(output_dir):
    if not os.path.exists('/mnt/subjectDir/sub-10159/func/nt_mc_RS.nii.gz'):
        print "%s: Running brain extraction for %s subject..." % (str(datetime_start), subject_id)    
        cmd = ['/bin/bash', '/mnt/motion_correction.sh']
        output=utils.run_command(cmd)   
        datetime_end = datetime.datetime.now()
        print "%s: Brain extraction FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "Brain extraction already found"
    
    return


def mango_visualization(image_path):
    cmd=['/bin/bash', '/mnt/Mango/mango', image_path]
    output=utils.run_command(cmd)
    print "Visualization FINISHED" 
    return

def motion_correction_plus_denoising(subject_id):
    if not os.path.exists('/mnt/subjectDir/sub-10159/func/nt_mc_RS.nii.gz'):
        print "%s: Running motion correction and denoising for %s subject..." % (str(datetime_start), subject_id)    
        cmd = ['/bin/bash', '/mnt/motion_correction.sh']
        output=utils.run_command(cmd)   
        datetime_end = datetime.datetime.now()
        print "%s: motion correction and denoising FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "Result of motion correction plus denoising already found"
    
    return 

def compare_tSNR_without_vs_with_denoising(output_dir):
    fig = plt.figure(figsize= (10, 12))
    #fig = plt.figure((4,4))
    
    #fig.suptitle('SUBCORTICAL SEGMENTATION', fontsize=20, fontweight='bold')   
    pic_title='tSNR maps (without vs with denoising)' 
    a=fig.add_subplot(2,1,1)
    a.axis('off')
    img = mpimg.imread('/mnt/tSNR_before_after_denoising.png')
    imgplot = plt.imshow(img)                  
    a.set_title(pic_title, fontsize=18) 
    
    a=fig.add_subplot(2,1,2)
    a.axis('off')
    img = mpimg.imread('/mnt/tSNR_heatmap_legend.png')
    imgplot = plt.imshow(img)
    plt.tight_layout( w_pad=1, h_pad=1)
    plt.show()
    return

def align_center(output_dir):
    if not os.path.exists('/mnt/subjectDir/sub-10159/func/nt_mc_RS.nii.gz'):
        print "%s: aligning center with ENIGMA templat for %s subject..." % (str(datetime_start), subject_id)    
        cmd = ['/bin/bash', '/mnt/motion_correction.sh']
        output=utils.run_command(cmd)   
        datetime_end = datetime.datetime.now()
        print "%s: Center alignment FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "Image with center aligned with ENIGMA template already found"
    
    return

def spatial_normalization(output_dir):
    if not os.path.exists('/mnt/subjectDir/sub-10159/func/nt_mc_RS.nii.gz'):
        print "%s: Running spatial normalization for %s subject..." % (str(datetime_start), subject_id)    
        cmd = ['/bin/bash', '/mnt/motion_correction.sh']
        output=utils.run_command(cmd)   
        datetime_end = datetime.datetime.now()
        print "%s: Spatial normalization FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "Image with spatial normalized already found"
    
    return


def compare_rsfMRI_before_vs_after_ali_reg(output_dir):
    fig = plt.figure(figsize= (10, 8))
    #fig = plt.figure((4,4))
    
    #fig.suptitle('SUBCORTICAL SEGMENTATION', fontsize=20, fontweight='bold')   
    pic_title='rsfMRIs before vs after alignment and registration' 
    a=fig.add_subplot(1,1,1)
    a.axis('off')
    img = mpimg.imread('/mnt/before_vs_after_alignment_registration.png')
    imgplot = plt.imshow(img)                  
    a.set_title(pic_title, fontsize=18) 
   
    plt.show()
    return   
def runANTsCorticalThicknessOn2D(slice_file, output_dir,template_dir,input_path):
    ''' Run ANTs Cortical Thickness Pipeline on 2D image'''
    input_path='/workspace/ANTs/antsCorticalThicknessExample/'
    # Run freesurfer
    datetime_start = datetime.datetime.now()
    print "%s: Running ANTs cortical Thickness pipeline for %s a 2D slice ..." % (str(datetime_start),slice_file)
    output_path=input_path+output_dir

    if not os.path.exists(output_path):
        cmd =['/bin/bash','/workspace/ANTs/antsCorticalThicknessExample/antsCorticalThicknessCommand.sh',input_path,template_dir,output_path,slice_file]
        output = utils.run_command(cmd)
        datetime_end = datetime.datetime.now()
        print "%s: ANTs FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "%s: ANTs results were already found for %s a 2D slice." % (str(datetime_start), slice_file)
        print "Running took about 20 minutes"
    
    
def runANTsCorticalThicknessOn3D(subject_ID,output_dir,template_dir,input_path):
    ''' Run ANTs Cortical Thickness Pipeline on 3D image'''
    input_path='/workspace/ANTs/antsCorticalThicknessExample/'
    T1w_mri_path="/mnt/subjectDir/"+subject_ID+"/anat/"+subject_ID+"_T1w.nii.gz"
    # Run freesurfer
    datetime_start = datetime.datetime.now()
    print "%s: Running ANTs cortical Thickness pipeline for %s ..." % (str(datetime_start),subject_ID)
    output_path=input_path+output_dir

    if not os.path.exists(output_path):
        cmd =['/bin/bash','/workspace/ANTs/antsCorticalThicknessExample/antsCorticalThicknessCommand3D.sh',input_path,template_dir,output_path,T1w_mri_path]
        output = utils.run_command(cmd)
        datetime_end = datetime.datetime.now()
        print "%s: ANTs FINISHED (Total time: %s)." % (str(datetime_end), str(datetime_end-datetime_start))
    else:
        print "%s: ANTs results were already found for %s." % (str(datetime_start), subject_ID)
        print "Running took about 6 hours"
        
        
   
    

                                        