# plugins/metasploit/app/metasploit.py
import uuid
import yaml
import re
import requests
import subprocess
from pathlib import Path
from aiohttp import web

class MetasploitHandler:
    def __init__(self, services):
        self.services = services
        self.ability_dir = Path('data/abilities/metasploit')
        self.ability_dir.mkdir(parents=True, exist_ok=True)
        self.module_root = Path('/opt/metasploit-framework/modules')
        self.api_key = "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"
        self.project_id = "proj_wSexKYXpW195fZDovsx3gKZ3"

    def extract_with_regex(self, ruby_code):
        cmd_exec_pattern = re.compile(r"cmd_exec\s*\(\s*['\"](.+?)['\"]\s*\)", re.DOTALL)
        return cmd_exec_pattern.findall(ruby_code)

    def extract_options(self, ruby_code):
        pattern = re.compile(r'register_options\s*\(\s*\[(.*?)\]\s*\)', re.DOTALL)
        match = pattern.search(ruby_code)
        if not match:
            return {}
        options_block = match.group(1)
        opts = re.findall(r'(OptString|OptInt|OptPort|Opt::[A-Z]+)\.new\(?[\'"](\w+)[\'"].*?[\'"](.+?)[\'"]', options_block, re.DOTALL)
        return {name: {"desc": desc, "required": True} for _, name, desc in opts}

    def map_option_to_variable(self, name):
        mapping = {
            'RHOSTS': '#{host.ip.address}',
            'RPORT': '#{host.port}',
            'LHOST': '#{server.ip}',
            'LPORT': '#{server.port}',
            'TARGETURI': '/',
            'USERNAME': '#{host.user.name}',
            'PASSWORD': '#{host.user.password}'
        }
        return mapping.get(name.upper(), f'#{name.lower()}')

    def extract_with_ai(self, ruby_code, options, module_path, target_env):
        opt_string = '\n'.join([f"{k}={v}" for k, v in options.items()])
        prompt = f"""
다음은 Metasploit Ruby 모듈입니다. 이 모듈의 경로는 `{module_path}` 입니다.
이 모듈의 기능을 분석하여 동일한 효과를 주는 Bash 명령어 한 줄을 생성하세요.

해당 모듈을 사용할 환경은 **{target_env}**입니다.
운영체제에 따라 다음과 같은 차이를 반영해 명령어를 생성해야 합니다:

- 예: `sudo` 그룹은 Ubuntu 계열에서는 `sudo`, Amazon Linux나 RHEL 계열에서는 `wheel`
- 예: `apt` 기반 시스템은 `/etc/apt`, RHEL 계열은 `/etc/yum` 또는 `/etc/dnf`
- 예: systemd가 없는 환경에선 `systemctl` 대신 `service`나 `init.d` 사용
- 예: 파일 경로나 사용자 권한 명령은 타겟 OS에 맞게 조정 필요

🧪 추가 조건:
- 생성된 명령어는 [ShellCheck](https://www.shellcheck.net/) 기준을 만족해야 합니다.
- Bash가 아닌 /bin/sh 환경에서도 오류 없이 작동해야 합니다.
- ShellCheck에서 오류가 발생할 가능성이 있다면 명령어를 다시 수정해도 됩니다.

제약 조건 (중요):
- 이 명령어는 Caldera ability의 'command' 필드에 삽입될 것
- 반드시 줄바꿈 없이 한 줄(one-liner)로 작성할 것
- /bin/sh 환경에서 syntax error 없이 정상 작동해야 함
- 다음 사항을 반드시 지킬 것:
  - USER=... 같은 쓸모없는 변수 선언 금지
  - RANDOM 사용 금지 — shuf만 사용할 것
  - $(...) 중첩 피하고, 명령문 안에서만 최소한으로 사용
  - 명령어는 반드시 실행 가능한 형태로 시작할 것 (예: echo, useradd, chmod)
  - 줄 끝에 && 같은 불필요한 연결자 쓰지 말 것
  - 코드 블록 (예: ```bash) 및 해설 포함 금지

📁 Metasploit 모듈 경로:
{module_path}

📄 Ruby 코드:
{ruby_code}

⚙️ 옵션:
{opt_string}

🎯 출력 형식:
**실행 가능한 Bash 명령어 한 줄만 출력하세요.**
"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Project": self.project_id,
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            res.raise_for_status()

            result = res.json()["choices"][0]["message"]["content"].strip()
            if result.startswith('```'):
                result = re.sub(r'```(?:bash)?\n?', '', result)
                result = result.replace('```', '').strip()

            one_liner = ' '.join(result.splitlines()).strip()
            print(one_liner)
            return [one_liner] if one_liner else []
        except Exception as e:
            print(f"[OpenAI ERROR] {e}")
            return []

    async def handle_search(self, request):
        try:
            data = await request.json()
            platform = data.get("platform")
            module_type = data.get("type")
            cve_year = data.get("cveYear")
            sort_by = data.get("sortBy")
            sort_order = data.get("sortOrder")

            search_terms = []
            if platform:
                search_terms.append(f"platform:{platform}")
            if module_type:
                search_terms.append(f"type:{module_type}")
            if cve_year:
                search_terms.append(f"cve:{cve_year}")

            sort_flags = ''
            if sort_by:
                sort_flags += f"-s {sort_by} "
            if sort_order == 'desc':
                sort_flags += "-r"

            query = f"search {' '.join(search_terms)} {sort_flags}".strip()
            cmd = f"echo '{query}' | /opt/metasploit-framework/msfconsole -q"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            modules = []
            for line in result.stdout.splitlines():
                if any(x in line for x in ['/linux/', '/windows/', '/multi/', '/android/']):
                    for part in line.strip().split():
                        if part.startswith(('exploit/', 'auxiliary/', 'post/', 'payload/', 'encoder/', 'nop/')):
                            modules.append(part)

            return web.json_response({'modules': modules})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_generate(self, request):
        try:
            data = await request.json()
            module_path = data.get('module')
            target_env = data.get('target_env', 'linux')
            options_input = data.get('options', {})
            if not module_path:
                return web.json_response({'error': 'No module selected'}, status=400)

            module_file = module_path.split('/')[-1] + '.rb'
            grep_cmd = f"find {self.module_root} -name '{module_file}'"
            found = subprocess.run(grep_cmd, shell=True, stdout=subprocess.PIPE, text=True)
            rb_files = found.stdout.strip().splitlines()
            if not rb_files:
                return web.json_response({'error': 'Module not found'}, status=404)

            ruby_code = Path(rb_files[0]).read_text()
            extracted_options = self.extract_options(ruby_code)
            full_options = {k: options_input.get(k) or self.map_option_to_variable(k) for k in extracted_options}

            commands = self.extract_with_regex(ruby_code)
            if not commands:
                commands = self.extract_with_ai(ruby_code, full_options, module_path, target_env)
            if not commands:
                return web.json_response({'error': 'No commands extracted'}, status=400)

            return web.json_response({
                'command': commands[0] if commands else '',
                'options': extracted_options
            })
        except Exception as e:
            return web.json_response({'error': f'Internal error: {str(e)}'}, status=500)

    async def handle_create_ability(self, request):
        try:
            data = await request.json()
            cmd = data.get('command')
            module_path = data.get('module', 'custom/generated')
            if not cmd:
                return web.json_response({'error': 'No command provided'}, status=400)

            ability = {
                'id': str(uuid.uuid4()),
                'name': f'{module_path} via GPT-edited Bash',
                'description': f'Generated Bash one-liner for module {module_path}',
                'tactic': data.get('tactic', 'execution'),
                'technique': {
                    'attack_id': data.get('technique_id', 'T1059'),
                    'name': data.get('technique_name', 'Command and Scripting Interpreter')
                },
                'platforms': {
                    'linux': {
                        'sh': {
                            'command': cmd
                        }
                    }
                }
            }

            ability_file = self.ability_dir / module_path.replace('/', '_')
            yml_path = ability_file.with_suffix('.yml')
            with open(yml_path, 'w') as f:
                yaml.dump([ability], f)

            await self.services.get('ability_svc').reload()
            return web.json_response({'status': 'ability created', 'path': str(yml_path)})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
