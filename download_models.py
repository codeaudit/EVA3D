import os
import html
import glob
import uuid
import hashlib
import requests
from tqdm import tqdm
from pdb import set_trace as st

eva3d_deepfashion_model = dict(file_url='https://drive.google.com/uc?id=1SYPjxnHz3XPRhTarx_Lw8SG_iz16QUMU',
                            alt_url='', file_size=160393221, file_md5='d0fae86edf76c52e94223bd3f39b2157',
                            file_path='checkpoint/512x256_deepfashion/volume_renderer/models_0420000.pt',)

smpl_model = dict(file_url='https://drive.google.com/uc?id=15XKYibakFcDgs_wEtLqS5dJYHck0FIv4',
                            alt_url='', file_size=39001280, file_md5='65dc7f162f3ef21a38637663c57e14a7',
                            file_path='smpl_models/smpl/SMPL_NEUTRAL.pkl',)

def download_pretrained_models():
    print('Downloading EVA3D model pretrained on DeepFashion.')
    with requests.Session() as session:
        try:
            download_file(session, eva3d_deepfashion_model)
        except:
            print('Google Drive download failed.\n' \
                  'Trying do download from alternate server')
            download_file(session, eva3d_deepfashion_model, use_alt_url=True)
    print('Downloading SMPL model.')
    with requests.Session() as session:
        try:
            download_file(session, smpl_model)
        except:
            print('Google Drive download failed.\n' \
                  'Trying do download from alternate server')
            download_file(session, smpl_model, use_alt_url=True)

def download_file(session, file_spec, use_alt_url=False, chunk_size=128, num_attempts=10):
    file_path = file_spec['file_path']
    if use_alt_url:
        file_url = file_spec['alt_url']
    else:
        file_url = file_spec['file_url']

    file_dir = os.path.dirname(file_path)
    tmp_path = file_path + '.tmp.' + uuid.uuid4().hex
    if file_dir:
        os.makedirs(file_dir, exist_ok=True)

    progress_bar = tqdm(total=file_spec['file_size'], unit='B', unit_scale=True)
    for attempts_left in reversed(range(num_attempts)):
        data_size = 0
        progress_bar.reset()
        try:
            # Download.
            data_md5 = hashlib.md5()
            with session.get(file_url, stream=True) as res:
                res.raise_for_status()
                with open(tmp_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=chunk_size<<10):
                        progress_bar.update(len(chunk))
                        f.write(chunk)
                        data_size += len(chunk)
                        data_md5.update(chunk)

            # Validate.
            if 'file_size' in file_spec and data_size != file_spec['file_size']:
                raise IOError('Incorrect file size', file_path)
            if 'file_md5' in file_spec and data_md5.hexdigest() != file_spec['file_md5']:
                raise IOError('Incorrect file MD5', file_path)
            break

        except Exception as e:
            print(e)
            # Last attempt => raise error.
            if not attempts_left:
                raise

            # Handle Google Drive virus checker nag.
            if data_size > 0 and data_size < 8192:
                with open(tmp_path, 'rb') as f:
                    data = f.read()
                links = [html.unescape(link) for link in data.decode('utf-8').split('"') if 'confirm=t' in link]
                if len(links) == 1:
                    file_url = requests.compat.urljoin(file_url, links[0])
                    continue

    progress_bar.close()

    # Rename temp file to the correct name.
    os.replace(tmp_path, file_path) # atomic

    # Attempt to clean up any leftover temps.
    for filename in glob.glob(file_path + '.tmp.*'):
        try:
            os.remove(filename)
        except:
            pass

if __name__ == "__main__":
    download_pretrained_models()
