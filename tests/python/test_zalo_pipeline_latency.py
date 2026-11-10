"""Offline regressions for idle polling, known chats, queue age and Windows cleanup."""
from _paths import ROOT, SERVER
import asyncio
import os
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

os.environ['AIVON_STATE_DIR'] = tempfile.mkdtemp(prefix='aivon-zalo-pipeline-')
import zalo_personal_channel as zc
from channels.zalo_personal import Transport
import conversations
import winproc
import mcp_orphans

CID = 'pipeline-test'
conn = {'id': CID, 'label': 'Test', 'connector_id': 'zalo'}

async def check():
    calls = []
    now = time.time()
    rows = [{'external_chat_id': 'customer', 'chat_type': 'private', 'title': 'Known customer', 'metadata': {}}]
    wire = {'id': 'fresh', 'threadId': 'customer', 'from': 'customer', 'text': 'Question',
            'type': 'text', 'ts': now * 1000}
    async def rpc(c, tool, args):
        calls.append(tool)
        assert tool != 'zalo_list_threads', 'Known chat blocked on contact refresh'
        return {'messages': [wire], 'cursor': 1}
    with patch.object(conversations, 'danh_sach', return_value=rows), patch.object(zc, '_goi', rpc), \
         patch.object(zc, '_ghi_lo', return_value=(1, 0)):
        await zc.doc_mot_lan(conn)
    assert calls == ['zalo_get_messages']
    assert zc._TT[CID]['ten']['customer']['type'] == 'dm'

    answered = []
    async def answer(text, meta, progress):
        answered.append(text)
        return {'text': 'ok'}
    tb = Transport(CID, [], answer, cfg_fn=lambda: {'reply_when': 'mention'})
    async def no_send(*args, **kwargs):
        pass
    tb._gui = no_send
    zc._BOTS[CID] = tb
    assert zc._nhip_cua(CID, now + 1000) == zc.NHIP_NHANH
    assert zc._nhip_cua('no-bot') == zc.NHIP

    # A message accepted while fresh must not expire merely because the quiet-window
    # wait carries its Zalo timestamp over the original 180-second boundary.
    event = {'account_id': CID, 'external_chat_id': 'customer', 'sender_type': 'customer',
             'sender_id': 'customer', 'sender_name': 'Customer', 'chat_type': 'private',
             'message_type': 'text', 'text': 'late but admitted', 'external_message_id': 'q1',
             'created_at': now - 179, 'metadata': {'pipeline_received_at': now}}
    zc._xep_cho(CID, event, now)
    with patch.object(zc, '_chay') as dispatch:
        assert zc.xa_hang_cho(CID, now + 6) == 1
        admitted = dispatch.call_args.args[1]
    with patch.object(zc.time, 'time', return_value=now + 6):
        await tb.xu_ly(admitted)
    assert answered == ['late but admitted']
    assert any(e['stage'] == 'processing' for e in zc._TT[CID]['pipeline'])

    old = dict(event, external_message_id='too-old', created_at=now - 500, metadata={})
    zc._xep_cho(CID, old, now)
    assert (CID, 'customer') not in zc._GOM
    assert zc._TT[CID]['pipeline'][-1]['reason'] == 'old_on_arrival'

asyncio.run(check())

if os.name == 'nt':
    import psutil
    # Real harmless process tree, with taskkill deliberately failing. The fallback
    # must actually kill the child as well as its parent.
    code = 'import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);print(p.pid,flush=True);time.sleep(60)'
    parent = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True,
                              creationflags=winproc.no_window())
    child = int(parent.stdout.readline())
    try:
        with patch.object(winproc.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            assert winproc.kill_tree(parent.pid)
        parent.wait(timeout=3)
        assert not psutil.pid_exists(child), 'Grandchild survived failed taskkill'
    finally:
        for pid in (child, parent.pid):
            try:
                psutil.Process(pid).kill()
            except psutil.NoSuchProcess:
                pass
    with patch.object(mcp_orphans.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, stdout='')):
        assert mcp_orphans._cmdline_windows(os.getpid()), 'WMI failure lost process identity'

print('Zalo pipeline regressions: OK')
