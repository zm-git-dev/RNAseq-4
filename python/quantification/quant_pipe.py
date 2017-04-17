import subprocess
import luigi
from os import path
import sys
import ConfigParser

ConfigFile = '/home/public/scripts/RNAseq/python/configure.ini'
conf = ConfigParser.ConfigParser()
conf.read(ConfigFile)

r_home = conf.get('server34', 'r_home')
kallisto_to_diff = conf.get('server34', 'kallisto_to_diff')

def run_cmd(cmd):
    p = subprocess.Popen(cmd, shell=False, universal_newlines=True, stdout=subprocess.PIPE)
    ret_code = p.wait()
    output = p.communicate()[0]
    return output

class prepare(luigi.Task):
    '''
    prepare directory and others
    '''
    def run(self):
        log_dir = path.join(OutDir, 'logs')
        kallisto_dir = path.join(OutDir, 'kallisto')

        tmp = run_cmd(['mkdir',
                        '-p',
                        log_dir,
                        kallisto_dir])
        with self.output().open('w') as prepare_logs:
            prepare_logs.write('prepare finished')

    def output(self):
        return luigi.LocalTarget('{}/logs/prepare.log'.format(OutDir))

class run_kallisto(luigi.Task):
    '''
    run kallisto
    '''

    sample = luigi.Parameter()

    def requires(self):
        return prepare()

    def run(self):
        tmp = run_cmd(['kallisto',
        'quant',
        '-i',
        '{}.kallisto_idx'.format(Transcript),
        '--bootstrap-samples=100',
        '--output-dir={0}/kallisto/{1}'.format(OutDir, self.sample),
        '{0}/{1}_1.clean.fq.gz'.format(CleanDir, self.sample),
        '{0}/{1}_2.clean.fq.gz'.format(CleanDir, self.sample),])

        with self.output().open('w') as run_kallisto_logs:
            run_kallisto_logs.write(tmp)

    def output(self):
        return luigi.LocalTarget('{0}/logs/{1}_kallisto.log'.format(OutDir, self.sample))

class run_diff(luigi.Task):

    '''
    run differential analysis and plot
    '''

    def requires(self):
        return [run_kallisto(sample = each_sample) for each_sample in sample_list]

    def run(self):
        tmp = run_cmd(['{}/Rscript'.format(r_home),
        kallisto_to_diff,
        '--quant_dir',
        '{}/kallisto'.format(OutDir),
        '--sample_inf',
        SampleInf,
        '--gene2tr',
        Gene2Tr,
        '--out_dir',
        OutDir])

        with self.output().open('w') as run_diff_logs:
            run_diff_logs.write(tmp)

    def output(self):
        return luigi.LocalTarget('{0}/logs/run_diff.log'.format(OutDir))


class quant_collection(luigi.Task):

    OutDir = luigi.Parameter()
    SampleInf = luigi.Parameter()
    CleanDir = luigi.Parameter()
    Transcript = luigi.Parameter()
    Gene2Tr = luigi.Parameter()

    def requires(self):
        global OutDir, SampleInf, CleanDir, sample_list, Transcript, Gene2Tr
        OutDir = self.OutDir
        SampleInf = self.SampleInf
        CleanDir = self.CleanDir
        Transcript = self.Transcript
        Gene2Tr = self.Gene2Tr
        sample_list = [each.strip().split()[1] for each in open(SampleInf)]
        return run_diff()

    def run(self):
        ignore_files = ['.ignore', 'logs', 'kallisto/*/run_info.json']
        with self.output().open('w') as ignore_inf:
            for each_file in ignore_files:
                ignore_inf.write('{}\n'.format(each_file))

    def output(self):
        return luigi.LocalTarget('{}/.ignore'.format(self.OutDir))

if __name__ == '__main__':
    luigi.run()
