import aiohttp
import asyncio
import uvicorn
import os
from fastai import *
from fastai.vision import *
from io import BytesIO
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles
import requests

# port
Port = int(os.environ.get('PORT', 50000))

export_file_url = 'https://drive.google.com/uc?export=download&id=1-9Ajk6OelCwkVnKMCkrU77JLVhn385RL'
export_file_name = 'model_classification.pkl'

classes = ["dengue","nao-dengue"]
path = Path('https://github.com/luanfrinhani/Unsplash100Labels').parent

app = Starlette()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])
app.mount('/static', StaticFiles(directory='app/static'))
app.mount('/prod-view', StaticFiles(directory='app/prod-view'))
# app.mount('/prod-view/components', StaticFiles(directory='app/prod-view/components'))


async def download_file(url, dest):
    if dest.exists(): return
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.read()
            with open(dest, 'wb') as f:
                f.write(data)


async def setup_learner():
    await download_file(export_file_url, path / export_file_name)
    try:
        learn = load_learner(path, export_file_name)
        return learn
    except RuntimeError as e:
        if len(e.args) > 0 and 'CPU-only machine' in e.args[0]:
            print(e)
            message = "\n\nThis model was trained with an old version of fastai and will not work in a CPU environment.\n\nPlease update the fastai library in your training environment and export your model again.\n\nSee instructions for 'Returning to work' at https://course.fast.ai."
            raise RuntimeError(message)
        else:
            raise

def sorted_prob(classes,probs):
  pairs = []
  for i,prob in enumerate(probs):
    pairs.append([prob.item(),i])
  pairs.sort(key = lambda o: o[0], reverse=True)
  return pairs

loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(setup_learner())]
learn = loop.run_until_complete(asyncio.gather(*tasks))[0]
loop.close()


@app.route('/')
async def homepage(request):
    html_file = path / 'view' / 'index.html'
    return HTMLResponse(html_file.open().read())


@app.route('/analyze', methods=['POST'])
async def analyze(request):
    img_data = await request.form()
    img_bytes = await (img_data['file'].read())
    img = open_image(BytesIO(img_bytes))

    prediction = learn.predict(img)[2]

    return JSONResponse({'result': str(prediction)})

if __name__ == '__main__':
    if 'serve' in sys.argv:
        uvicorn.run(app=app, host='0.0.0.0', port=Port, log_level="info")
