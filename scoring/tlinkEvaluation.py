'''
Created on Dec 26, 2011

@author: Weiyi Sun

Provides some alternative ways to evaluates system output Tlinks against gold standard Tlinks:

The temporal closure in this script is completed using SputLink (SputLink citation?) 

- usage:
  $ python tlinkEvaluation.py [--oc] [--oo] [--cc] goldstandard_xml_filename system_output_xml_filename
  
  --oc: Original against Closure:
        -Precision: the total number of system output Tlinks that can be verified in the gold standard closure
                    divided by the total number of system output Tlinks
        -Recall: the total number gold standard output Tlinks that can be verified in the system closure
                 divided by the total number of gold standard output Tlinks
  --oo: Origianl against Orignal:
        -Precision: the total number of system output Tlinks that can be verified in the gold standard output
                    divided by the total number of system output Tlinks
        -Recall: the total number gold standard output Tlinks that can be verified in the system output
                 divided by the total number of gold standard output Tlinks  
  --cc: Closure against Closuer:
        -Precision: the total number of system closure Tlinks that can be verified in the gold standard closure
                    divided by the total number of system output Tlinks
        -Recall: the total number gold standard closure Tlinks that can be verified in the system closure
                 divided by the total number of gold standard output Tlinks  
'''
import sys

if sys.version_info<(2,7):
    print "Error: This evaluation script requires Python 2.7 or higher"
else:
    import argparse
    import os
    import re
    import time
    import subprocess
    
    
    header = """<fragment>
    <TEXT>
    """
    
    footer = """
    </fragment>"""
    
    _DEBUG = True
    #_DEBUG = False
    
    def open_file(fname):
        if os.path.exists(fname):
            f = open(fname)
            return f
        else:
            outerror("No such file: %s" % fname)
            return None
        
    def outerror(text):
        #sys.stderr.write(text + "\n")
        raise Exception(text)
    
    def attr_by_line(tlinkline):
        """
        Args:
          line - str: MAE TLINK tag line,
                      e.g. <TLINK id="TL70" fromID="E28" fromText="her erythema"
                       toID="E26" toText="erythema on her left leg" type="OVERLAP" />
        """
        tuple=re.split('^<TLINK id=\"|\" fromID=\"|\" fromText=\"|\" toID=\"|\" toText=\"|\" type=\"|\" />$',tlinkline)
        id=tuple[1]
        fromid=tuple[2]
        toid=tuple[4]
        type=tuple[6]
        type=type.replace('SIMULTANEOUS','OVERLAP')
        return id, fromid, toid, type
    
    def attr_by_closure(cline): #event to event
        """
        Args:
          line - str: Sputlink closure tag line,
                      e.g. <TLINK origin=" i" toEID="E49" fromEID="E48" relType="SIMULTANEOUS"/>
        """
        re_exp = 'origin=\"([^"]*)\"\s+to[ET]ID=\"([^"]*)\"\s+from[ET]ID=\"([^"]*)\"\s+relType=\"([^"]*)\"+\/>'
        m = re.search(re_exp, cline)
        if m:
            id, toid, fromid, type = m.groups()
        else:
            raise Exception("Malformed EtoE tag: %s" % (cline))
        type=type.replace('SIMULTANEOUS','OVERLAP')
        return fromid, toid, type
    
    def attr_by_closure2(cline): #event to timex
        """
        Args:
          line - str: Sputlink closure tag line,
                      e.g. <TLINK fromTID="T12" origin=" i" toEID="E32" relType="SIMULTANEOUS"/>
        """
        re_exp = 'from[TE]ID=\"([^"]*)\"\s+origin=\"([^"]*)\"\s+to[ET]ID=\"([^"]*)\"\s+relType=\"([^"]*)\"+\/>'
        m = re.search(re_exp, cline)
        if m:
            fromid, id, toid, type = m.groups()
        else:
            raise Exception("Malformed EtoT tag: %s" % (cline))
        type=type.replace('SIMULTANEOUS','OVERLAP')
        return fromid, toid, type
    
    def get_tlinks(text_fname):
        '''
        Args:
            text_fname: file name of the MAE xml file
        
        Output:
            a tlinks tuple of all the tlinks in the file 
        '''
        tf=open(text_fname)
        lines = tf.readlines()
        tlinks=[]
        for line in lines:  
            if re.search('<TLINK',line):
                tlink_tuple=attr_by_line(line)
                tlinks.append(tlink_tuple)
        return tlinks
    
    def get_tlinks_closure(text_fname):
        '''
        Args:
            text_fname: file name of the tlink closure xml file
        
        Output:
            a tlinks tuple of all the valid tlink output in the closure     
        '''
        clines = open('sputlink/'+text_fname+'.closure.xml').readlines()
        closed_tlinks=get_tlinks(text_fname)
        existing_tlinks=closed_tlinks
        for i in range(len(existing_tlinks)):
            existing_tlinks[i]=existing_tlinks[1:]
        for cline in clines:
            if not re.search('<TLINK origin|relType=\"\"|relType=\"INCLUDES\"',cline): #T to E or T to T
                if re.search('<TLINK fromTID',cline): 
                    id=''
                    if re.search('origin=\"closure\"',cline):
                        id="closure"
                    elif re.search('origin=\" i\"',cline):
                        id="inverse"
                    elif re.search('origin=\"\"',cline):
                        id="default"
                    if id<>'':
                        closed_tlink_tuple=attr_by_closure2(cline)
                        if closed_tlink_tuple not in existing_tlinks:
                            fromid, toid, type=closed_tlink_tuple
                            closed_tlinks.append([id,fromid, toid, type])
                            existing_tlinks.append([closed_tlink_tuple])
            elif not re.search('relType=\"\"|relType=\"INCLUDES\"',cline): # E to E or E to T
                if re.search('origin=\"closure\"',cline):
                    id="closure"
                elif re.search('origin=\" i\"',cline):
                    id="inverse"
                elif re.search('origin=\"\"',cline):
                    id="default"
                if id<>'':
                    closed_tlink_tuple=attr_by_closure(cline)
                    if closed_tlink_tuple not in existing_tlinks:
                        fromid, toid, type=closed_tlink_tuple
                        closed_tlinks.append([id,fromid, toid, type])
                        existing_tlinks.append([closed_tlink_tuple])     
        return closed_tlinks
    
    def compare_tlinks(text_fname1, text_fname2, dic, option='OrigVsClosure'):
        '''
        This function verifies whether the TLinks in text_fname1 can be found in text_fname2
        using the evaluation method in 'option' arg:
        
        Args:
            text_fname1:    filename of the first xml file 
            text_fname2:    filename of the second xml file
            dic:            a dictionary that maps extent id in the first file to
                            the corresponding extent id in the second file
            option:         OrigVsClosure | ClosureVsClosure | OrigVsOrig
        
        Output:
            totalcomlinks:    Total number of comparable Tlinks (tlinks whose extents 
                              were annotated by both xml files)
            totalmatch:       Total number of matched tlinks 
        '''
        if option == 'OrigVsClosure':
            tlinks_tuple1=get_tlinks_closure(text_fname1)
            tlinks_tuple2=get_tlinks(text_fname2)
        elif option=='ClosureVsClosure':
            tlinks_tuple1=get_tlinks_closure(text_fname1)
            tlinks_tuple2=get_tlinks_closure(text_fname2)
        elif option=='OrigVsOrig':
            tlinks_tuple1=get_tlinks(text_fname1)
            tlinks_tuple2=get_tlinks(text_fname2)
        
        totalcomlinks=0
        totalmatch=0
    
        for tlinks2 in tlinks_tuple2:
            if len(tlinks2)==4:
                
                linkid2=tlinks2[0]
                fromid2=tlinks2[1]
                toid2=tlinks2[2]
                if toid2 not in ['Admission','Discharge'] and fromid2<>'' and toid2<>'' and linkid2.find('R')==-1 and fromid2.find('S')==-1 and toid2.find('S')==-1:
                    if dic=={}:
                        fromid = fromid2
                        toid = toid2
                    else:
                        fromid = dic[fromid2]
                        toid = dic[toid2]
                    type2=tlinks2[3]
                    if fromid=="" or toid=="":
                        pass            
                    else:
                        type1=""
                        match=0
                        for tlinks1 in tlinks_tuple1:
                            if len(tlinks1)==4:
                                if fromid==tlinks1[1] and toid==tlinks1[2]:
                                    type1=tlinks1[3]
                                    totalcomlinks+=1
                                    if type2==type1:
                                        match=1
                                        totalmatch+=match
                                        break
        return totalcomlinks, totalmatch
    
    def tlinkClosurePreprocess(text_fname):
        '''
        process the xml file and output it in a format that can be
        processed in SputLink. The output file will be placed in the
        SputLink directory. 
            e.g. input file dir1/dir2/file
                 output file sputlink/dir1/dir2/file
        
        Args:
            text_fname: name of the MAE xml file to be processed
        '''
        tf = open_file(text_fname)
        lines=tf.readlines()
        fdir=text_fname.split('/')[0:-1]
        currentdir="sputlink/"
        for subdir in fdir:
            if subdir<>'':
                if not os.path.isdir(currentdir+subdir):
                    subprocess.call(['mkdir',currentdir+subdir])
                    currentdir+=subdir+'/'
                else:
                    currentdir+=subdir+'/'
        nfname="sputlink/"+text_fname+'.pcd.xml'
        nf=open(nfname, 'w')
        nf.write(header)
        count=3
        for i in range(3, len(lines)):      
            if not re.search("]]><",lines[i]): 
                nf.write(lines[i])
                count+=1
            else:
                nf.write("</TEXT>\n")
                break
        count+=2
        for i in range(count, len(lines)):      
            if re.search("<EVENT id",lines[i]): 
                lines[i]=lines[i].replace(" type=", " eventType=")
                pre,post=lines[i].split(" id=")
                outline=pre+" eid="+post
                nf.write(outline)     
            elif re.search("<TIMEX3 id",lines[i]):  
                lines[i]=lines[i].replace(" type=", " timexType=")
                pre,post=lines[i].split(" id=")
                outline=pre+" tid="+post
                nf.write(outline)     
            elif re.search("<SECTIME",lines[i]):
                lines[i]=lines[i].replace(" type=", " secType=")   
                nf.write(lines[i])  
            elif re.search("<TLINK",lines[i]):
                pre,mid1=lines[i].split(" id=")
                outline=pre+" lid="
                if not re.search(" fromID=\"E",mid1):
                    mid1, mid2=mid1.split(" fromID=")
                    outline+=mid1+" fromTID="
                else:
                    mid1, mid2=mid1.split(" fromID=")
                    outline+=mid1+" fromEID="
                if not re.search(" toID=\"E",mid2):
                    mid2, mid3=mid2.split(" toID=")
                    outline+=mid2+" toTID="
                else:
                    mid2, mid3=mid2.split(" toID=")
                    outline+=mid2+" toEID="
                mid3, post=mid3.split(" type=")
                outline+=mid3
                if re.search('AFTER',post):
                    outline+=" type=\"AFTER\" ></TLINK>\n"
                elif re.search('BEFORE',post):
                    outline+=" type=\"BEFORE\" ></TLINK>\n"
                elif re.search('OVERLAP',post):
                    outline+=" type=\"SIMULTANEOUS\" ></TLINK>\n"   
                nf.write(outline)         
        nf.write(footer)
    
    def tlinkEvaluation(gold_fname, system_fname, option, goldDic={}, sysDic={}):
        
        tlinkClosurePreprocess(gold_fname)
        tlinkClosurePreprocess(system_fname)
        precLinkCount, precMatchCount, recLinkCount, recMatchCount= [0, 0, 0, 0]
        if option=='OrigVsOrig':
    
            precLinkCount, precMatchCount = compare_tlinks(gold_fname, system_fname, sysDic, option)
            recLinkCount, recMatchCount = compare_tlinks(system_fname, gold_fname, goldDic, option)
            
            if precLinkCount>0:
                precision=float(precMatchCount)/precLinkCount
            if recLinkCount>0:
                recall=float(recMatchCount)/recLinkCount
    
        else:
            if not os.path.isfile("sputlink/"+gold_fname+'.closure.xml'):
                root=os.getcwd()
                path=root+"/sputlink/"
                os.chdir(path)
                nf=open('sputlink.temp','w')
                subprocess.call(['perl','merge.pl',gold_fname+'.pcd.xml',gold_fname+'.closure.xml'],stdout=nf,stderr=nf)
                nf.close()
                subprocess.call(['rm','sputlink.temp'])
                os.chdir(root)
            if not os.path.isfile("sputlink/"+system_fname+'.closure.xml'):
                root=os.getcwd()
                path=root+"/sputlink/"
                os.chdir(path)
                nf=open('sputlink.temp','w')
                subprocess.call(['perl','merge.pl',system_fname+'.pcd.xml',system_fname+'.closure.xml'],stdout=nf,stderr=nf)
                nf.close()
                subprocess.call(['rm','sputlink.temp'])
                os.chdir(root)
            if  os.path.isfile("sputlink/"+gold_fname+'.closure.xml') and os.path.isfile("sputlink/"+system_fname+'.closure.xml'):
            
                precLinkCount, precMatchCount = compare_tlinks(gold_fname, system_fname, sysDic, option)
                recLinkCount, recMatchCount = compare_tlinks(system_fname, gold_fname, goldDic, option)
                
                if precLinkCount>0:
                    precision=float(precMatchCount)/precLinkCount
                if recLinkCount>0:
                    recall=float(recMatchCount)/recLinkCount
            
        return precLinkCount, recLinkCount, precMatchCount,  recMatchCount
        
    if __name__ == '__main__':
        usage= "%prog [options] [goldstandard-file] [systemOutput-file]" + __doc__
        parser = argparse.ArgumentParser(description='Evaluate system output Tlinks against gold standard Tlinks.')
        parser.add_argument('file', type=str, nargs=2,\
                         help='the file or directory of the gold standard xml file(s), or the system output xml file(s)')
        parser.add_argument('--cc', dest='evaluation_option', action='store_const',\
                          const='cc', default='oc', help='select different types of tlink evaluation: oc - original against closure; cc - closure against closure; oo - original against original (default: oc)')
        parser.add_argument('--oc', dest='evaluation_option', action='store_const',\
                          const='oc', default='oc', help='select different types of tlink evaluation: oc - original against closure; cc - closure against closure; oo - original against original (default: oc)')
        parser.add_argument('--oo', dest='evaluation_option', action='store_const',\
                          const='oo', default='oc', help='select different types of tlink evaluation: oc - original against closure; cc - closure against closure; oo - original against original (default: oc)')
          
        args = parser.parse_args()
        # run on a single file
        if len(args.file_des) == 2:
            gold, system = args.file
            if args.evaluation_option=='oo':
                precLinkCount, recLinkCount, precMatchCount,  recMatchCount=tlinkEvaluation(gold, system,'OrigVsOrig')
            elif args.evaluation_option=='cc':
                precLinkCount, recLinkCount, precMatchCount,  recMatchCount=tlinkEvaluation(gold, system,'ClosureVsClosure')
            elif args.evaluation_option=='oc':
                precLinkCount, recLinkCount, precMatchCount,  recMatchCount=tlinkEvaluation(gold, system,'OrigVsClosure')
            print     """
            Total number of comparable Tlinks: 
               Gold Standard : \t"""+str(recLinkCount)+"""
               System Output : \t"""+str(precLinkCount)+"""
            --------------
            Recall : \t\t"""+'{:.2}'.format(1.0*recMatchCount/recLinkCount)+"""
            Precision: \t\t""" + '{:.2}'.format(1.0*precMatchCount/precLinkCount)+'\n'
        else:
            print "Error: Please input exactly 2 arguments: gold_standard_filename, system_file_name"
