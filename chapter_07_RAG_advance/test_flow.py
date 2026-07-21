import sys; sys.path.insert(0,'.')
from app import app, config
import os, json

app.secret_key = 'test'
app.config['TESTING'] = True

with app.test_client() as c:
    # Upload
    c.post('/upload', data={'file':(open('testcase/vwo_test_cases_5000.csv','rb'),'vwo.csv')})
    files = [f for f in os.listdir('data/uploads') if f.endswith('.csv') and f != '.gitkeep']
    c.post('/ingest', data={'filename': files[-1], 'text_cols': ['title','steps','expected'], 'meta_cols': ['id','jira_id','priority','module']})

    # Try SSE stream, read first event
    r = c.get('/ingest/stream')
    print('SSE:', r.status_code, r.content_type)
    gen = r.response
    try:
        for i, chunk in enumerate(gen):
            if i >= 3: break
            text = chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
            print(f'Event {i}:', text[:300])
    except Exception as e:
        print('SSE read error:', e)

    # Chunks page
    r = c.get('/chunks')
    print('Chunks:', r.status_code)

    # Chat page
    r = c.get('/chat')
    print('Chat:', r.status_code)
