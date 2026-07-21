import sys; sys.path.insert(0,'.')
from app import app
import os

app.secret_key = 'test'
c = app.test_client()

c.post('/upload', data={'file':(open('testcase/vwo_test_cases_5000.csv','rb'),'vwo.csv')})
files = [f for f in os.listdir('data/uploads') if f.endswith('.csv') and f != '.gitkeep']
c.post('/ingest', data={'filename': files[-1], 'text_cols': ['title','steps','expected'], 'meta_cols': ['id','jira_id','priority','module']})

r = c.get('/ingest/stream')
i = 0
for line in r.response:
    text = line.decode('utf-8') if isinstance(line, bytes) else str(line)
    if text.strip():
        print(repr(text[:250]))
        i += 1
        if i >= 4: break
print('---DONE---')
