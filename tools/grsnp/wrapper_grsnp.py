"""
Adapted from rgFastqc.py

called as
  <command interpreter="python">
    rgFastqc.py -i $input_file -d $html_file.files_path -o $html_file -n "$out_prefix"
  </command>


"""
import re
import os
import sys
import subprocess
import optparse
import shutil
import tempfile
import zipfile
import gzip


def getFileString(fpath, outpath):
    """
    format a nice file size string
    """
    size = ''
    fp = os.path.join(outpath, fpath)
    s = '? ?'
    if os.path.isfile(fp):
        n = float(os.path.getsize(fp))
        if n > 2**20:
            size = ' (%1.1f MB)' % (n/2**20)
        elif n > 2**10:
            size = ' (%1.1f KB)' % (n/2**10)
        elif n > 0:
            size = ' (%d B)' % (int(n))
        s = '%s %s' % (fpath, size) 
    return s


class GRSNP():
    """wrapper
    """
    
    
    def __init__(self,opts=None):
        assert opts <> None
        self.opts = opts
        
        
    def run_grsnp(self,foi_paths,gf_paths,background):
        """       

        """        
        dummy,tlog = tempfile.mkstemp(prefix='grsnp',suffix=".log",dir=self.opts.outputdir)       
        com = ["python","-m","grsnp.hypergeom4",foi_paths,gf_paths,background,'-p']
        p = subprocess.Popen(com,shell=False,stderr=sys.stdout,stdout=sys.stdout,cwd=self.opts.outputdir)
        retval = p.wait()
        runlog = open(tlog,'r').readline()
        grs.prep_html_heatmaps() # create the heatmap html result file
        flist = os.listdir(self.opts.outputdir)
        self.fix_datasetnames()
        excludefiles = ['.prog','? ?']
        flist = [x for x in flist if not x in excludefiles]
        html = self.fix_grsnp(flist,runlog)
        return html,retval
        

        
    def fix_grsnp(self,flist=[],runlog=[]):
        """ add some of our stuff to the html
        """
        res = ['<div class="module"><h2>Files created by GenomeRunner SNP</h2><table cellspacing="2" cellpadding="2">\n']
        flist.sort()
        for i,f in enumerate(flist):
             if not(os.path.isdir(f)):
                 fn = os.path.split(f)[-1]
                 res.append('<tr><td><a href="%s">%s</a></td></tr>\n' % (fn,getFileString(fn, self.opts.outputdir)))
        res.append('</table>\n') 
        res.append('<a href="grsnpinfilename">Original GenomeRunner SNP can be found here</a><br/><hr/>\n')
        res.append('</div>')
        return res # with our additions


    def prep_html_heatmaps(self):
        ''' Places the heatmap json data in a results html template file. 
        '''
        html_header = open(os.path.join(os.path.dirname(__file__),"results_template.html")).read()
        html_res_path = os.path.join(self.opts.outputdir,"heatmaps.html")
        h_j_path = os.path.join(self.opts.outputdir,"clustered.json")
        c_j_path = os.path.join(self.opts.outputdir,"pcc_matrix.json")
        # read in json heatmap data
        str_heat = open(h_j_path).read()
        str_heat_cor = open(c_j_path).read()
        # delete the json files, don't want these in the results
        os.remove(h_j_path)
        os.remove(c_j_path)
        # write out the heatmap html file
        with open(html_res_path,'wb') as writer:
            writer.write(html_header+"""<script type="text/javascript">
                    $(function () {
                        $('#heatmap').heatmap({
                            json: """+ str_heat +"""
                        });
                        $('#heatmap_cor').heatmap({
                            json: """+ str_heat_cor +"""
                        });
                    });
                    </script>
                </head>
                <body>
                    <ul class="nav nav-tabs">       
                        <li><a href="#heatmap" data-toggle="tab">Enrichment Heatmap</a></li>
                        <li><a href="#heatmap_cor" data-toggle="tab">Pearsons Correlation Heatmap</a></li>
                    </ul>
                    <div class="tab-content">
                        <div class="tab-pane active" style="padding-left:10em" id="heatmap"></div>
                        <div class="tab-pane" style="padding-left:10em" id="heatmap_cor"></div>
                    </div>
                </body>
                </html>""")




    def fix_datasetnames(self):
        """ Used to replace the dataset code names (assigned by Galaxy) in the output files
        with the original filenames in all of the output files.
        """
        result_files = []
        fois = [x.strip() for x in self.opts.fois.split(",")]
        gfs = [x.strip() for x in self.opts.gfs.split(",")]
        for base, dirs, files in os.walk(self.opts.outputdir):
            result_files += [os.path.join(base,x) for x in files]
        # Go through result file content and rename Galaxy data_set with the correct file names.
        for f in result_files:
            old_content = open(f).read()
            with open(f,"wb") as writer:
                for line in old_content.split("\n"):
                    tmp = line
                    # rename FOIs
                    for i in range(len(fois)):
                        tmp = tmp.replace(base_name(fois[i]), self.opts.foi_names[i])
                    # rename genomic features
                    for i in range(len(self.opts.gf_names)):
                        tmp = tmp.replace(base_name(gfs[i]), self.opts.gf_names[i])
                    writer.write(tmp + "\n")
        # rename filenames that were given Galaxy data_set names
        with open(os.path.join(self.opts.outputdir,"enrichment","name_conversion.txt"),'wb') as writer:
            for i in range(len(fois)):
                writer.write(base_name(fois[i]) + "\t" + base_name(self.opts.foi_names[i])+"\n")
            for i in range(len(self.opts.gf_names)):
                writer.write(base_name(gfs[i]) + "\t" + base_name(self.opts.gf_names[i])+"\n")



    

def base_name(k):
    return os.path.basename(k).split(".")[0]

if __name__ == '__main__':
    op = optparse.OptionParser()
    op.add_option('-f', '--fois', default=None)
    op.add_option('--foi_names', default=None)
    op.add_option('-g', '--gfs', default=None)
    op.add_option('--gf_names', default=None)
    op.add_option('-b', '--bg_path', default=None)
    op.add_option('--bg_name', default=None)
    op.add_option('-o', '--htmloutput', default=None)
    op.add_option('-d', '--outputdir', default="")
    op.add_option('-n', '--namejob')
    opts, args = op.parse_args()
    if not os.path.exists(opts.outputdir): 
        os.makedirs(opts.outputdir)
    opts.foi_names = [x.strip() for x in opts.foi_names.split(",") if x != None and x.strip() != ""]
    opts.gf_names = [x.strip() for x in opts.gf_names.split(",") if x != None and x.strip() != ""]
    opts.gfs = ",".join([x.strip() for x in opts.gfs.split(",") if x != None and x.strip() != ""])
    opts.fois = ",".join([x.strip() for x in opts.fois.split(",") if x != None and x.strip() != ""])
    print opts
    grs = GRSNP(opts) 
    html,retval = grs.run_grsnp(opts.fois,opts.gfs,opts.bg_path)    
    f = open(opts.htmloutput, 'w')
    f.write(''.join(html))
    f.close()
    if retval <> 0:
         print >> sys.stderr, serr # indicate failure