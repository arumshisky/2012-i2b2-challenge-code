'''
Created on Dec 25, 2011

@author: Weiyi Sun


Evaluates system output Events against gold standard Events

- usage:
  $ python eventEvaluation.py goldstandard_xml_filename system_output_xml_filename
  
  - Overlapping extents are considered matches
  - Recall:
       number of EVENTs in system output that overlap with gold standard EVENT extents
  - Precision:
       number of gold standard EVENTs that overlap with EVENTs in the system output 
  - Attribute score:
       accuracy for each attribute, computed over all matching EVENTs: i.e.
       the percentage of correct attribute values in system output
       e.g. system outputs 5 events, 3 of which can be verified in the goldstandard
            2 out of the 3 have the same Event 'type' attribute as the goldstandard
            the system type match score will be 2/3=66.6%    
'''

import sys

if sys.version_info<(2,7):
    print "Error: This evaluation script requires Python 2.7 or higher"
else:
        
    import argparse
    import os
    import re
    
    #_DEBUG = True
    _DEBUG = False
    
    punctuationsStr= ", . ? ! \" \' < > ; : / \\ ~ _ - + = ( ) [ ] { } | @ # $ % ^ & * ` &apos; &amp; &quot; &gt; &lt;"
    punctuations=punctuationsStr.split()
    
    def open_file(fname):
        if os.path.exists(fname):
            f = open(fname)
            return f
        else:
            outerror("No such file: %s" % fname)
            return None
        
    def list_dir(dirname):
        if os.path.exists(dirname):
            return os.listdir(dirname)
        else:
            outerror("No such file: %s" % dirname)
            return None
        
    def outerror(text):
        #sys.stderr.write(text + "\n")
        raise Exception(text)
    
    def attr_by_line(event_line):
        """
        Args:
          line - str: MAE EVENT tag line,
                      e.g. <EVENT id="E22" start="1400" end="1418"
                      text="supplemental oxygen" modality="FACTUAL"
                      polarity="POS" type="TREATMENT" />
        """
        re_exp = 'id=\"([^"]*)\"\s+start=\"([^"]*)\"\s+end=\"([^"]*)\"\s+text=\"([^"]*)\"\s+modality=\"([^"]*)\"\s+polarity=\"([^"]*)\"\s+type=\"([^"]*)\"\s+\/>'
        m = re.search(re_exp, event_line)
        if m:
            id, start, end, text, context_mod, polarity, event_type = m.groups()
        else:
            raise Exception("Malformed EVENT tag: %s" % (event_line))
        return id, start, end, text, context_mod, polarity, event_type
    
    def get_events(text_fname):
        tf=open_file(text_fname)
        lines = tf.readlines()
        events=[]
        for line in lines:  
            if re.search('<EVENT',line):
                event_tuple=attr_by_line(line)
                events.append(event_tuple)
        return events
            
    def compare_events(text_fname1,text_fname2,option):
        '''
        This function verifies whether the Events in efname1 can be found in efname2:
        
        Args:
            text_fname1: filename of the first xml file 
            text_fname2: filename of the second xml file 
            option:      exact, overlap or partialCredit match
        
        Output:
            totalEvents:         total number of Events in the first file
            matchEvents:         total number of Events in the first file 
                                 that can be found in the second file
            tspanPartcialCredit: same as above, but discount overlap Event matches 
                                 (as 0.5), and exact match as 1
            ttyp:                number of correct type in the first file
            tpol:                number of correct polarity in the first file
            tmod:                number of correct modality in the first file
            dic:                 a dictionary that maps events id in efname1
                                 to the corresponding id in efname2
        '''
        events1=get_events(text_fname1)
        events2=get_events(text_fname2)
        dic={}
        totalEvents=len(events1)
        matchEvents=0
        tspanPartcialCredit=0
        tmod=0
        tpol=0
        ttyp=0
        exactmatch=0
        for event_tuple1 in events1:
            if event_tuple1<>['']:
                spanScore=0
                id1, startStr1, endStr1, text1, modality1, polarity1, type1=event_tuple1
                id2, startStr2, endStr2, text2, modality2, polarity2, type2=["", "", "", "", "", "", ""]
                dic[id1]=''
                start1=int(startStr1)
                end1=int(endStr1)
                for event_tuple2 in events2:
                    if event_tuple2<>['']:
                        id2, startStr2, endStr2, text2, modality2, polarity2, type2=event_tuple2
                        start2=int(startStr2)
                        end2=int(endStr2)
                        words1=text1.split()
                        words2=text2.split()
                        for punctuation in punctuations:
                            while punctuation in words1:
                                words1.remove(punctuation)
                            while punctuation in words2:
                                words2.remove(punctuation)
                        if start1<=start2: 
                            if end1>=start2+1:
                                spanScore=0.5
                                if words1==words2:
                                    spanScore=1   
                                break
                        else:
                            if end2>start1+1:
                                spanScore=0.5
                                if words1==words2:
                                    spanScore=1                       
                                break
                modality=0
                polarity=0
                type=0
                if option=='exact':
                    if spanScore==1:
                        matchEvents+=1
                        dic[id1]=id2
                        if modality1.upper()==modality2.upper():
                            modality=1
                        if polarity1.upper()==polarity2.upper():
                            polarity=1   
                        if type1.upper()==type2.upper():
                            type=1
                else:
                    if spanScore>0:
                        matchEvents+=1
                        dic[id1]=id2
                        if modality1.upper()==modality2.upper():
                            modality=1
                        if polarity1.upper()==polarity2.upper():
                            polarity=1   
                        if type1.upper()==type2.upper():
                            type=1                              
                tspanPartcialCredit+=spanScore
                tmod+=modality
                tpol+=polarity
                ttyp+=type
            
        return totalEvents, matchEvents, tspanPartcialCredit, tmod, tpol, ttyp,dic
        
        
        
    def eventEvaluation(gold_fname, system_fname, option):
        '''
        evaluate a system output xml file against its corresponding goldstandard file:
        
        Args:
            gold_fname:      filename of the gold standard xml file
            system_fname:    filename of the system output xml file
            option:          exact, overlap or partialCredit match
        
        Output:
            goldDic:        a dictionary that map Event id in goldstardard to those
                            in the system output
            systemDic:      a dictionary that map Event id in system outpt to those
                            in the gold standard
            goldEventCount: total number of EVENT annotated in the gold standard
            systemEventCount: total number of EVENT marked in the system output
            precCount:      system matched EVENT found in gold standard 
            recallCount:    gold standard matched EVENT found in system 
            recallType:     correct type count in gold standard matched EVENT found in system 
            recallPol:      correct polarity count in gold standard matched EVENT found in system 
            recallMod:      correct modality count in gold standard matched EVENT found in system 
            recallPC:       partial credit recall match
            precPC:         partial credit precision match
        '''
        tf1 = open_file(gold_fname)
        tf2 = open_file(system_fname)
        if tf1 and tf2:
            goldEventCount, recallCount, recallPC, recallMod, recallPol, recallType, goldDic=compare_events(gold_fname, system_fname,option)
            systemEventCount, precCount, precPC, precMod, precPol, precType, systemDic=compare_events(system_fname, gold_fname,option)
            if goldEventCount<>0:
                if option=='partialCredit':
                    recall=float(recallPC)/goldEventCount
                else:
                    recall=float(recallCount)/goldEventCount
            else:
                recall=0
            if systemEventCount<>0:
                if option=='partialCredit':
                    precision=float(precPC)/systemEventCount
                else:
                    precision=float(precCount)/systemEventCount
            else:
                precision=0
            #attribute score: percentage of the correct attribute in total matched # of event. same as temp eval 2
            if recallCount<>0:
                typeScore=float(recallType)/recallCount
                polScore=float(recallPol)/recallCount
                modScore=float(recallMod)/recallCount
            else:
                typeScore=0
                polScore=0
                modScore=0
            averagePR=((recall*goldEventCount)+(precision*systemEventCount))/(goldEventCount+systemEventCount)
            fScore=2*(precision*recall)/(precision+recall)
            print("""
            Total number of events: 
               Gold Standard: \t\t"""+str(goldEventCount)+"""
               System Output: \t\t"""+str(systemEventCount)+"""
            --------------
            Recall : \t\t\t"""+'{:.2}'.format(recall)+"""
            Precision : \t\t""" + '{:.2}'.format(precision)+"""
            Average P&R : \t\t"""+'{:.2}'.format(averagePR)+"""
            F measure : \t\t"""+'{:.2}'.format(fScore)+"""
            --------------
            modality match score :\t"""+'{:.2}'.format(modScore)+"""
            Polarity match score :\t"""+'{:.2}'.format(polScore)+"""
            Type match score :\t\t"""+'{:.2}'.format(typeScore)+"\n")
            return goldDic, systemDic, goldEventCount,systemEventCount,precCount,recallCount,recallType,recallPol,recallMod,recallPC, precPC
    
    if __name__ == '__main__':
        usage= "%prog [options] [goldstandard-file] [systemOutput-file]" + __doc__
        parser = argparse.ArgumentParser(description='Evaluate system output EVENTs against gold standard EVENTs.')
        parser.add_argument('gold_file', type=str, nargs=1,\
                         help='the file or directory of the gold standard xml file')
        parser.add_argument('system_file', type=str, nargs=1,\
                         help='the file or directory of the system output xml file')
           
        args = parser.parse_args()
        
        # run on a single file
        if 1:
            gold=args.gold_file[0]
            system=args.system_file[0]
            eventEvaluation(gold, system,'overlap')
            print "Warning: This script calculates overlapping event span match between two files only. Please use the i2b2Evaluation.py script instead for more options."
        