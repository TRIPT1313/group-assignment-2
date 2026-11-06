"""Unit-cost STRIPS state-space search for the supplied PDDL domain.
A*: admissible relaxed shortest-visit lower bound + unavoidable actions.
Greedy best-first: same heuristic, priority h only. PDDL plans replay-validated.
Note: deposit is restricted to Base in search: any solution depositing a rock elsewhere
can be shortened or preserved by deferring that deposit until Base, so optimality is retained.
"""
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import heapq, time, json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
LOC=['Base','SiteA','SiteB','SiteC','SiteD','SiteE','SiteF']
EDGES=[('Base','SiteA'),('Base','SiteB'),('SiteA','SiteC'),('SiteB','SiteD'),('SiteC','SiteE'),('SiteD','SiteE'),('SiteE','SiteF')]
ARCS=EDGES+[(b,a) for a,b in EDGES]+[('SiteC','SiteD')]
ROCK_LOCS=['SiteA','SiteB','SiteC','SiteD','SiteF','SiteE','SiteF']
HARD={2,4,6}

def problem_pddl(extended):
 n=7 if extended else 5
 arcs=[(a,b) for a,b in ARCS if not (extended and {a,b}=={'Base','SiteB'})]
 facts=['(at Curiosity Base)','(drill-at Drill1 SiteE)','(bay-empty Bay1)','(bay-empty Bay2)']
 facts += [f'(connected {a} {b})' for a,b in arcs]
 facts += [f'(rock-at Rock{i+1} {ROCK_LOCS[i]})' for i in range(n)]
 facts += [f'({"hard" if i in HARD else "soft"} Rock{i+1})' for i in range(n)]
 rocks=' '.join(f'Rock{i}' for i in range(1,n+1))
 goal=' '.join(f'(rock-at Rock{i} Base)' for i in range(1,n+1))
 return f'''(define (problem mars-rover-{"extended" if extended else "original"})
 (:domain mars-rover)
 (:objects Curiosity - rover Drill1 - drill Bay1 Bay2 - bay
           {' '.join(LOC)} - location
           {rocks} - rock)
 (:init {' '.join(facts)})
 (:goal (and (at Curiosity Base) (bay-empty Bay1) (bay-empty Bay2) {goal}))
)\n'''

class Planner:
 def __init__(self,extended):
  self.extended=extended;self.n=7 if extended else 5
  self.edges=[(a,b) for a,b in ARCS if not (extended and {a,b}=={'Base','SiteB'})]
  self.neigh=defaultdict(list)
  for a,b in self.edges:self.neigh[a].append(b)
  self.dist={(a,b):(0 if a==b else 999) for a in LOC for b in LOC}
  for a,b in self.edges:self.dist[a,b]=1
  for k in LOC:
   for i in LOC:
    for j in LOC:self.dist[i,j]=min(self.dist[i,j],self.dist[i,k]+self.dist[k,j])
  self.start=('Base',False,tuple([0]*self.n))
  self.goal_status=tuple([3]*self.n)
 def goal(self,s):return s[0]=='Base' and s[2]==self.goal_status
 def options(self,s):
  loc,drill,rocks=s
  for nxt in self.neigh[loc]:yield ('move Curiosity '+loc+' '+nxt).split(),(nxt,drill,rocks)
  if loc=='SiteE' and not drill:yield ['pick-drill','Curiosity','Drill1','SiteE'],(loc,True,rocks)
  occupied={r for r in rocks if r in (1,2)}
  for i,st in enumerate(rocks):
   if st!=0 or ROCK_LOCS[i]!=loc or (i in HARD and not drill):continue
   for bay in (1,2):
    if bay in occupied:continue
    new=list(rocks);new[i]=bay
    yield [f'collect-{"hard" if i in HARD else "soft"}','Curiosity',f'Rock{i+1}',loc,f'Bay{bay}'],(loc,drill,tuple(new))
  if loc=='Base':
   for i,st in enumerate(rocks):
    if st not in (1,2):continue
    new=list(rocks);new[i]=3
    yield ['deposit','Curiosity',f'Rock{i+1}','Base',f'Bay{st}'],(loc,drill,tuple(new))
 @lru_cache(None)
 def route_lower_bound(self,loc,targets):
  if not targets:return self.dist[loc,'Base']
  best=999
  for ix,t in enumerate(targets):best=min(best,self.dist[loc,t]+self.route_lower_bound(t,targets[:ix]+targets[ix+1:]))
  return best
 @lru_cache(None)
 def heuristic(self,s):
  loc,drill,rocks=s
  outstanding={ROCK_LOCS[i] for i,st in enumerate(rocks) if st==0}
  need_drill=not drill and any(i in HARD and st==0 for i,st in enumerate(rocks))
  if need_drill: outstanding.add('SiteE')
  move_lb=self.route_lower_bound(loc,tuple(sorted(outstanding)))
  actions=sum(2 if st==0 else 1 if st in (1,2) else 0 for st in rocks)
  return move_lb+actions+(1 if need_drill else 0)
 def solve(self,method,limit=2000000):
  t0=time.perf_counter();start=self.start
  g={start:0};prev={};counter=0;expanded=0
  heap=[(self.heuristic(start),counter,start)]
  while heap:
   priority,_,s=heapq.heappop(heap)
   if s in prev and prev[s] is None:continue
   if self.goal(s):
    steps=[];cur=s
    while cur!=start:
     parent,act=prev[cur];steps.append(act);cur=parent
    steps.reverse()
    return {'strategy':method,'plan':[f'({" ".join(act)})' for act in steps],'length':len(steps),'total_actions':len(steps),'states_expanded':expanded,'planning_seconds':round(time.perf_counter()-t0,6),'states_generated':len(g)}
   expanded+=1
   if expanded>limit:raise RuntimeError(f'Exceeded {limit} expanded for {method}')
   for act,child in self.options(s):
    new_g=g[s]+1
    if child in g and g[child]<=new_g:continue
    g[child]=new_g;prev[child]=(s,act);counter+=1
    score=(new_g+self.heuristic(child)) if method=='A* optimal' else self.heuristic(child)
    heapq.heappush(heap,(score,counter,child))
  raise RuntimeError('No plan found')
 def validate(self,plan):
  state=self.start; trace=[]
  for k,line in enumerate(plan,1):
   act=line.strip('()').split()
   choices=list(self.options(state))
   match=[s for a,s in choices if a==act]
   if not match:raise AssertionError(f'Invalid action {k}: {line}; state={state}')
   state=match[0]
   trace.append(f'{k:02d}: {line} => rover={state[0]}, drill={state[1]}, rock statuses={state[2]}')
  assert self.goal(state),state
  assert all(x==3 for x in state[2]) and state[0]=='Base'
  return {'valid':True,'rover_at':state[0],'drill_carried':state[1], 'rock_locations':{f'Rock{i+1}':'Base' for i in range(self.n)},'Bay1':'Empty','Bay2':'Empty','trace':trace}

def main():
 (ROOT/'Problem2_PDDL'/'Problem.pddl').write_text(problem_pddl(False))
 (ROOT/'Problem2_PDDL'/'Problem_extended.pddl').write_text(problem_pddl(True))
 summary={}
 for ext in [False,True]:
  p=Planner(ext);sc='extended' if ext else 'original'
  summary[sc]={}
  for method in ['Greedy best-first','A* optimal']:
   name='greedy' if method.startswith('Greedy') else 'optimal'
   result=p.solve(method)
   verification=p.validate(result['plan'])
   base=OUT/'tables'/f'{sc}_{name}'
   base.with_suffix('.plan').write_text('\n'.join(result['plan'])+'\n')
   base.with_suffix('.json').write_text(json.dumps({**result,'verification':{k:v for k,v in verification.items() if k!='trace'}},indent=2))
   (OUT/'screenshots'/f'{sc}_{name}_planner_output.txt').write_text(json.dumps({k:v for k,v in result.items() if k!='plan'},indent=2)+'\n\nPLAN:\n'+'\n'.join(result['plan'])+'\n\nVALIDATOR:\n'+'\n'.join(verification['trace'])+'\nFINAL STATE: '+json.dumps({k:v for k,v in verification.items() if k!='trace'},indent=2))
   summary[sc][name]={k:v for k,v in result.items() if k!='plan'}
   print(sc,name,result['length'],result['states_expanded'],result['planning_seconds'],'VALID',flush=True)
 (OUT/'tables'/'planner_summary.json').write_text(json.dumps(summary,indent=2))
 return summary
if __name__=='__main__':main()
