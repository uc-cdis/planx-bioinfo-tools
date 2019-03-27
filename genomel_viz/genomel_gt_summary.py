import pandas as pd
summary=pd.read_csv('mel_pos_gt_summary.tsv', sep='\t')
summary.columns=['pos','homo_ref_count','het_count','homo_alt_count']
summary['homo_ref']=summary['homo_ref_count']/(summary['homo_ref_count']+ summary['het_count']+summary['homo_alt_count'])
summary['het']=summary['het_count']/(summary['homo_ref_count']+ summary['het_count']+summary['homo_alt_count'])
summary['homo_alt']=summary['homo_alt_count']/(summary['homo_ref_count']+ summary['het_count']+summary['homo_alt_count'])
select=summary[['pos','homo_ref','het','homo_alt']]
select1=select[(select.het!=0) |(select.homo_alt!=0)]
select2=select1.stack()
select2.to_csv('stacked_frequency_3086352.csv')