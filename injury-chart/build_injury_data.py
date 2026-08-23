#!/usr/bin/env python3
import csv, gzip, io, json, urllib.request
from pathlib import Path

SEASON = 2025
OUT = Path(__file__).with_name('injury-data.json')
BASE = 'https://raw.githubusercontent.com/withqwerty/availability-data/main/raw/GB1/2025/'
GAMES = 'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz'
TEAMS = [
 ('AFC Bournemouth','afc-bournemouth'),('Arsenal','fc-arsenal'),('Aston Villa','aston-villa'),
 ('Brentford','fc-brentford'),('Brighton','brighton-amp-hove-albion'),('Burnley','fc-burnley'),
 ('Chelsea','fc-chelsea'),('Crystal Palace','crystal-palace'),('Everton','fc-everton'),('Fulham','fc-fulham'),
 ('Leeds United','leeds-united'),('Liverpool','fc-liverpool'),('Manchester City','manchester-city'),
 ('Manchester United','manchester-united'),('Newcastle United','newcastle-united'),
 ('Nottingham Forest','nottingham-forest'),('Sunderland','afc-sunderland'),('Tottenham','tottenham-hotspur'),
 ('West Ham','west-ham-united'),('Wolves','wolverhampton-wanderers')
]

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req,timeout=120) as r: return r.read()

print('Downloading games…')
games_bytes=get(GAMES)
rows=[]
with gzip.GzipFile(fileobj=io.BytesIO(games_bytes)) as gz:
    txt=io.TextIOWrapper(gz,encoding='utf-8-sig')
    for r in csv.DictReader(txt):
        try: season=int(r.get('season','0') or 0)
        except: continue
        if season==SEASON: rows.append(r)
print('Season games:',len(rows))

def gi(r,k,default=None):
    v=r.get(k)
    if v in (None,''): return default
    try:return int(float(v))
    except:return default

def game_for_club(r,cid):
    return gi(r,'home_club_id')==cid or gi(r,'away_club_id')==cid

def game_date(r): return r.get('date','9999-12-31')

def opponent_score(r,cid):
    home=gi(r,'home_club_id'); away=gi(r,'away_club_id')
    hg=r.get('home_club_goals',''); ag=r.get('away_club_goals','')
    hn=r.get('home_club_name') or str(home); an=r.get('away_club_name') or str(away)
    if home==cid: return an, f'{hg}-{ag}', 'H'
    return hn, f'{ag}-{hg}', 'A'

allclubs={}
for display,slug in TEAMS:
    print('Club',display)
    data=json.loads(get(BASE+slug+'.json').decode('utf-8'))
    cid=int(data['tmId'])
    recs=[]
    for comp in data.get('competitions',[]):
        code=comp.get('code')
        players=comp.get('players',[])
        n=max([len(p.get('matches',[])) for p in players] or [0])
        compgames=[r for r in rows if r.get('competition_id')==code and game_for_club(r,cid)]
        compgames.sort(key=game_date)
        for i in range(n):
            injured=[]; round_label=''
            for p in players:
                ms=p.get('matches',[])
                if i>=len(ms): continue
                m=ms[i]
                if not round_label: round_label=str(m.get('round',''))
                if m.get('status')=='injured':
                    injured.append({'name':p.get('name','Unknown'),'position':p.get('position',''),'detail':m.get('detail','')})
            g=compgames[i] if i<len(compgames) else None
            if g:
                opp,score,venue=opponent_score(g,cid)
                date=g.get('date','')
                game_id=g.get('game_id','')
            else:
                opp='Unknown';score='';venue='';date='9999-12-31';game_id=''
            recs.append({'date':date,'competition':comp.get('name',code),'competitionCode':code,'round':round_label,
                         'opponent':opp,'score':score,'venue':venue,'gameId':game_id,'injured':injured})
    recs.sort(key=lambda x:(x['date'],x['competitionCode'],x['round']))
    for j,r in enumerate(recs,1): r['match']=j; r['count']=len(r['injured'])
    allclubs[display]={'club':display,'tmId':cid,'matches':recs}

payload={'season':'2025/26','method':'Transfermarkt Periods of Absence status=injured paired positionally with Transfermarkt games within each competition, then sorted by date','clubs':allclubs}
OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('Wrote',OUT,OUT.stat().st_size,'bytes')
