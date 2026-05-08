/**
 * 问答对话API
 */
import request from './index'

/** 发送问题（RAG问答） */
export function askQuestion(data) {
  return request.post('/chat/ask', data, {
    timeout: 3600000
  })
}

/** 发送问题（RAG流式问答） */
export async function askQuestionStream(data, handlers = {}) {
  const token = sessionStorage.getItem('token')
  const response = await fetch('/api/chat/ask/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(data)
  })

  if (!response.ok || !response.body) {
    throw new Error('网络异常')
  }

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    const res = await response.json()
    throw new Error(res.message || '请求失败')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const handleEvent = (rawEvent) => {
    const lines = rawEvent.split('\n')
    const eventLine = lines.find((line) => line.startsWith('event:'))
    const dataLines = lines.filter((line) => line.startsWith('data:'))
    if (!eventLine || dataLines.length === 0) return

    const event = eventLine.slice(6).trim()
    if (event === 'ping') return

    const payload = JSON.parse(dataLines.map((line) => line.slice(5).trim()).join('\n'))

    if (event === 'answer_delta') handlers.onDelta?.(payload.delta || '')
    if (event === 'source_docs') handlers.onSources?.(payload.source_docs || [])
    if (event === 'done') handlers.onDone?.(payload)
    if (event === 'error') throw new Error(payload.message || '问答服务异常')
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const event of events) {
      handleEvent(event)
    }

    if (done) {
      if (buffer.trim()) handleEvent(buffer)
      break
    }
  }
}

/** 获取对话历史列表 */
export function getChatHistory(params) {
  return request.get('/chat/history', { params })
}

/** 获取指定会话的对话记录 */
export function getSessionChats(sessionId) {
  return request.get(`/chat/session/${sessionId}`)
}
