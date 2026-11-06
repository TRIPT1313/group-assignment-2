"""Problem 1: exact discrete BN inference, ancestral sampling, MLE and BDeu (ESS=10).
No pgmpy is required: the estimator and inference routines are implemented explicitly.
"""
from pathlib import Path
from itertools import product
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs'
SEED = 2026
VARS = ['Weather','DayType','Occupancy','AC','ApplianceLoad','EnergyConsumption']
STATES = {'Weather':['Hot','Mild','Cold'],'DayType':['Weekday','Weekend'], 'Occupancy':['High','Low'], 'AC':['On','Off'], 'ApplianceLoad':['Heavy','Light'], 'EnergyConsumption':['High','Low']}
PARENTS = {'Weather':[], 'DayType':[], 'Occupancy':['DayType'], 'AC':['Weather','Occupancy'], 'ApplianceLoad':['Occupancy'], 'EnergyConsumption':['AC','ApplianceLoad']}
PROBS = {
 'Weather': {():[.5,.3,.2]}, 'DayType':{():[.7,.3]},
 'Occupancy':{('Weekday',):[.45,.55],('Weekend',):[.8,.2]},
 'AC':{('Hot','High'):[.9,.1],('Hot','Low'):[.6,.4],('Mild','High'):[.4,.6],('Mild','Low'):[.15,.85],('Cold','High'):[.1,.9],('Cold','Low'):[.05,.95]},
 'ApplianceLoad':{('High',):[.75,.25],('Low',):[.35,.65]},
 'EnergyConsumption':{('On','Heavy'):[.92,.08],('On','Light'):[.68,.32],('Off','Heavy'):[.55,.45],('Off','Light'):[.12,.88]}
}
QUERIES = [
 ('Q1',{'EnergyConsumption':'High'},{}),
 ('Q2',{'EnergyConsumption':'High'},{'Weather':'Hot'}),
 ('Q3',{'EnergyConsumption':'High'},{'DayType':'Weekend'}),
 ('Q4',{'EnergyConsumption':'High'},{'Weather':'Cold','Occupancy':'High'}),
 ('Q5',{'Weather':'Hot'},{'EnergyConsumption':'High'}),
 ('Q6',{'AC':'On'},{'EnergyConsumption':'High'}),
 ('Q7',{'AC':'On'},{'EnergyConsumption':'High','ApplianceLoad':'Heavy'})]

def check_cpts(cpts):
 for node in VARS:
  expected = list(product(*[STATES[p] for p in PARENTS[node]]))
  assert set(cpts[node]) == set(expected), f'missing CPT configs for {node}'
  for parent, vals in cpts[node].items():
   assert len(vals)==len(STATES[node]) and all(0<=v<=1 for v in vals) and abs(sum(vals)-1)<1e-10, (node,parent,vals)
 return True

def joint_probability(row,cpts):
 p = 1.
 for node in VARS:
  p *= cpts[node][tuple(row[x] for x in PARENTS[node])][STATES[node].index(row[node])]
 return p

ALL_ROWS=[dict(zip(VARS,x)) for x in product(*[STATES[x] for x in VARS])]
def probability(target, evidence, cpts):
 denominator=numerator=0.
 for r in ALL_ROWS:
  p=joint_probability(r,cpts)
  if all(r[k]==v for k,v in evidence.items()):
   denominator+=p
   if all(r[k]==v for k,v in target.items()):numerator+=p
 if denominator==0: raise ValueError('zero probability evidence')
 return numerator/denominator

def query_values(cpts):return {q:probability(t,e,cpts) for q,t,e in QUERIES}

def sample(n,rng):
 rows=[]
 for i in range(n):
  row={}
  for node in VARS:
   probs=PROBS[node][tuple(row[x] for x in PARENTS[node])]
   row[node]=rng.choice(STATES[node],p=probs)
  rows.append(row)
 return pd.DataFrame(rows,columns=VARS)

def fit(df, estimator, ess=10.):
 result={}
 for node in VARS:
  result[node]={}
  configurations=list(product(*[STATES[p] for p in PARENTS[node]]))
  r=len(STATES[node]);q=len(configurations)
  alpha=(ess/(q*r)) if estimator=='BDeu' else 0.
  for cfg in configurations:
   mask=np.ones(len(df), dtype=bool)
   for p,s in zip(PARENTS[node],cfg):mask &= (df[p].to_numpy()==s)
   counts=np.array([(df[node].to_numpy()[mask]==v).sum() for v in STATES[node]],float)
   denominator=counts.sum()+alpha*r
   if denominator==0:
    # MLE is unidentifiable for unobserved parent configurations; use uniform explicit fallback.
    arr=np.ones(r)/r
   else:arr=(counts+alpha)/denominator
   result[node][cfg]=arr.tolist()
 check_cpts(result)
 return result

def manual_q1():
 # Sum over occupancy & weather, marginalizing day type; sum over AC and load conditional on O and W.
 result=0; lines=[]
 for w in STATES['Weather']:
  for o in STATES['Occupancy']:
   po=sum(PROBS['DayType'][()][STATES['DayType'].index(d)]*PROBS['Occupancy'][(d,)][STATES['Occupancy'].index(o)] for d in STATES['DayType'])
   ac=PROBS['AC'][(w,o)][0]; load=PROBS['ApplianceLoad'][(o,)][0]
   inner=ac*load*.92+ac*(1-load)*.68+(1-ac)*load*.55+(1-ac)*(1-load)*.12
   term=PROBS['Weather'][()][STATES['Weather'].index(w)]*po*inner
   result+=term;lines.append((w,o,po,inner,term))
 return result,lines

def cpt_ac_table(cpts):
 return {f'{w}/{o}':cpts['AC'][(w,o)][0] for w in STATES['Weather'] for o in STATES['Occupancy']}

def main():
 for d in ['plots','tables','screenshots']: (OUT/d).mkdir(parents=True,exist_ok=True)
 check_cpts(PROBS)
 print('All expert CPTs normalized: PASS')
 expert=query_values(PROBS)
 manually,steps=manual_q1()
 assert abs(manually-expert['Q1'])<1e-10
 (OUT/'tables'/'q1_manual_calculation.txt').write_text('P(O=High)=0.70*0.45+0.30*0.80=0.555; P(O=Low)=0.445\n'
  +'P(E=High)=sum_{w,o} P(w) P(o) sum_{a,l} P(a|w,o) P(l|o) P(E=High|a,l)\n'
  +'Inner(a,l) = pAC*pLoad*.92+pAC*(1-pLoad)*.68+(1-pAC)*pLoad*.55+(1-pAC)*(1-pLoad)*.12\n'
  +'\n'.join(f'{w:5} {o:5}: P(o)={po:.6f}; P(E=High|w,o)={inner:.8f}; contribution={term:.9f}' for w,o,po,inner,term in steps)
  +f'\nTOTAL Q1 = {manually:.10f}\n')
 # d-separation checks with actual inference
 tests={
 '1 Weather independent DayType':(probability({'Weather':'Hot'},{},PROBS),probability({'Weather':'Hot'},{'DayType':'Weekend'},PROBS)),
 '2 Weather independent DayType GIVEN E':(probability({'Weather':'Hot'},{'EnergyConsumption':'High'},PROBS),probability({'Weather':'Hot'},{'EnergyConsumption':'High','DayType':'Weekend'},PROBS)),
 '3 Weather independent Load GIVEN Occupancy':(probability({'Weather':'Hot'},{'Occupancy':'High'},PROBS),probability({'Weather':'Hot'},{'Occupancy':'High','ApplianceLoad':'Heavy'},PROBS))}
 (OUT/'tables'/'independence_checks.txt').write_text('\n'.join(f'{k}: {x:.10f} vs {y:.10f}; equal={abs(x-y)<1e-10}' for k,(x,y) in tests.items())+'\n')
 graph=nx.DiGraph([(p,v) for v in VARS for p in PARENTS[v]])
 fig,ax=plt.subplots(figsize=(11,5.4))
 positions={'Weather':(0,2),'DayType':(0,0),'Occupancy':(1.1,0),'AC':(2.25,2),'ApplianceLoad':(2.25,0),'EnergyConsumption':(3.7,1)}
 nx.draw_networkx(graph,pos=positions,ax=ax,arrows=True,arrowsize=23,node_size=3300,node_color='#D8EBFC',edgecolors='#36608A',font_size=9,font_weight='bold',width=2)
 ax.set_title('Expert Bayesian Network: Smart-Home Energy',fontsize=15);ax.axis('off');fig.tight_layout();fig.savefig(OUT/'plots'/'bayesian_network.png',dpi=180);plt.close(fig)
 rng=np.random.default_rng(SEED)
 summary=[]; errors=[]; all_comparisons=[]
 for n in (500,5000,20000):
  df=sample(n,rng);df.to_csv(OUT/'tables'/f'synthetic_{n}.csv',index=False)
  weather=df['Weather'].value_counts(normalize=True).reindex(STATES['Weather']).fillna(0)
  combos=df.groupby(['Weather','Occupancy']).size().reindex(pd.MultiIndex.from_product([STATES['Weather'],STATES['Occupancy']]),fill_value=0)
  for w in STATES['Weather']:
   summary.append({'Samples':n,'Weather':w,'Frequency':weather[w], 'HighOccupancyCount':int(combos[w,'High']),'LowOccupancyCount':int(combos[w,'Low'])})
  learned={method:fit(df,method) for method in ('MLE','BDeu')}
  ac=pd.DataFrame({'Weather/Occupancy':list(cpt_ac_table(PROBS)),'Expert':list(cpt_ac_table(PROBS).values()),'MLE':[cpt_ac_table(learned['MLE'])[x] for x in cpt_ac_table(PROBS)],'Bayesian BDeu':[cpt_ac_table(learned['BDeu'])[x] for x in cpt_ac_table(PROBS)]})
  ac.to_csv(OUT/'tables'/f'ac_cpt_{n}.csv',index=False)
  m=query_values(learned['MLE']);b=query_values(learned['BDeu'])
  for q in expert:
   all_comparisons.append({'Samples':n,'Query':q,'Expert':expert[q],'MLE':m[q],'Bayesian':b[q], '|Diff| MLE':abs(m[q]-expert[q]),'|Diff| Bayesian':abs(b[q]-expert[q])})
  for method,vals in [('MLE',m),('Bayesian',b)]: errors.append({'Samples':n,'Estimator':method,'MeanAbsoluteDifference':float(np.mean([abs(vals[q]-expert[q]) for q in expert]))})
  fig,ax=plt.subplots(figsize=(9,4)); x=np.arange(len(ac));wd=.26
  for i,col in enumerate(('Expert','MLE','Bayesian BDeu')):ax.bar(x+(i-1)*wd,ac[col],wd,label=col)
  ax.set_xticks(x,ac['Weather/Occupancy'],rotation=20);ax.set_ylabel('P(AC = On)');ax.set_ylim(0,1.05);ax.legend();ax.set_title(f'AC CPT comparison, n={n}');fig.tight_layout();fig.savefig(OUT/'plots'/f'ac_cpt_{n}.png',dpi=160);plt.close(fig)
 pd.DataFrame(summary).to_csv(OUT/'tables'/'sampling_summary.csv',index=False)
 comp=pd.DataFrame(all_comparisons);comp.to_csv(OUT/'tables'/'query_comparisons.csv',index=False)
 err=pd.DataFrame(errors);err.to_csv(OUT/'tables'/'mean_absolute_differences.csv',index=False)
 fig,ax=plt.subplots(figsize=(8,5))
 for meth in ['MLE','Bayesian']:
  x=err[err.Estimator==meth];ax.plot(x.Samples,x.MeanAbsoluteDifference,'o-',label=meth,linewidth=2)
 ax.set_xscale('log');ax.set_xticks([500,5000,20000]);ax.set_xticklabels(['500','5,000','20,000']);ax.set_xlabel('Training samples');ax.set_ylabel('Mean absolute difference over Q1–Q7');ax.set_title('Expert versus learned query error');ax.legend();ax.grid(alpha=.25);fig.tight_layout();fig.savefig(OUT/'plots'/'estimator_errors.png',dpi=180);plt.close(fig)
 most=comp[comp.Samples==500]
 worst={meth:most.loc[most[col].idxmax(),['Query',col]].to_dict() for meth,col in [('MLE','|Diff| MLE'),('Bayesian','|Diff| Bayesian')]}
 p4=probability({'Weather':'Cold','Occupancy':'High'},{},PROBS)
 p7=probability({'EnergyConsumption':'High','ApplianceLoad':'Heavy'},{},PROBS)
 explanation=f'''PART A: Expert inference\n{json.dumps(expert,indent=2)}\nAll CPT columns sum to one: PASS. Manual Q1: {manually:.10f} (matches exact inference).\nQ6 versus Q7: {expert['Q6']:.6f} vs {expert['Q7']:.6f}. Given high energy, AC and appliance load become dependent because they share a common effect (E), an explaining-away collider. Observing heavy load makes AC use less necessary as an explanation, so the posterior P(AC=On) decreases here.\n\nPART B: D-SEPARATION\n1. TRUE: W -> A -> E <- L <- O <- D is blocked at the unobserved collider E; W -> A <- O <- D is blocked at A. W and D are distinct independent roots.\n2. FALSE: observing E opens the collider W -> A -> E <- L <- O <- D; additionally E's descendant status opens the collider W -> A <- O <- D. Numerical values:\n3. TRUE: conditioning on O blocks W -> A <- O -> L and W -> A -> E <- L (collider E unobserved).\n{(OUT/'tables'/'independence_checks.txt').read_text()}\n\nPART E: COMPARATIVE INTERPRETATION\nMean absolute differences:\n{err.to_string(index=False)}\nLargest errors with 500 samples: {worst}. The query with the largest error depends on the realized sample; rare evidence amplifies estimation variance. Specifically P(W=Cold,O=High)={p4:.4f} (about {500*p4:.1f} examples in 500), and P(E=High,L=Heavy)={p7:.4f} (about {500*p7:.1f} examples). Note that evidence rarity is one reason, not a guarantee that a specific query is the worst.\nBDeu uses a uniform Dirichlet pseudo-count ESS=10 spread over parent configurations, smoothing sparse cells and generally improving calibration with small datasets, but may increase bias if the true CPT is far from uniform. Empirical performance for this seed is visible in the table; MLE may occasionally outperform Bayesian due to sampling noise. Error typically decreases as sample size increases.\n\nSampling seed: {SEED}. Datasets generated consecutively from one seeded NumPy RNG, in topological order.\n'''
 (OUT/'tables'/'bayesian_analysis.txt').write_text(explanation)
 print(explanation)
 print('DONE Problem 1')
if __name__=='__main__':main()
