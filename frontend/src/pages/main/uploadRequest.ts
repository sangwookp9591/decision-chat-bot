import { csrfToken, idempotencyKey } from '../../api/client';

export function uploadRequest(data: FormData, onProgress: (value: number) => void, path = '/api/requests') {
  return new Promise<{ request_id: string; status: string; revision: number }>((resolve, reject) => {
    const xhr = new XMLHttpRequest(); xhr.open('POST', path); xhr.withCredentials = true;
    xhr.setRequestHeader('Idempotency-Key', idempotencyKey()['Idempotency-Key']); const token = csrfToken(); if (token) xhr.setRequestHeader('X-CSRF-Token', token);
    xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100)); };
    xhr.onerror = () => reject(new Error('서버에 연결할 수 없습니다.'));
    xhr.onload = () => { if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText)); else reject(new Error('요청을 접수하지 못했습니다.')); };
    xhr.send(data);
  });
}
