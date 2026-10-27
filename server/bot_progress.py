"""A delayed, throttled acknowledgement while a Zalo answer is still running."""
import asyncio

async def answer(answer_fn, text, meta, notify, trace=None, *, delay=15, interval=120):
    state = {'text':'Em đã nhận yêu cầu và đang xử lý. Nếu cần nghiên cứu hoặc tạo tài liệu, em sẽ gửi kết quả tại đây khi hoàn tất.'}
    async def progress(message):
        name = str(message or '')
        if trace:
            trace(name.rsplit(':',1)[-1].strip()[:80])
        if 'search' in name or 'fetch' in name:
            state['text']='Em đang tìm và đối chiếu nguồn để lập báo cáo. Hoàn tất em sẽ gửi kết quả tại đây.'
        elif 'create' in name:
            state['text']='Em đang tổng hợp dữ liệu và tạo file báo cáo.'
        elif 'send' in name:
            state['text']='Em đang gửi file báo cáo vào cuộc trò chuyện này.'
        elif 'soạn' in name:
            state['text']='Em đang hoàn tất câu trả lời.'
    async def ticker():
        await asyncio.sleep(delay)
        for _ in range(3):
            try:
                await notify(state['text'])
            except Exception:
                pass  # A progress notification must never break the actual answer.
            await asyncio.sleep(interval)
    task = asyncio.create_task(ticker())
    try:
        return await answer_fn(text, meta, progress)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
