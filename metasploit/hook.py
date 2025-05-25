# plugins/metasploit/hook.py
from plugins.metasploit.app.metasploit import MetasploitHandler

name = 'Metasploit'
description = 'Metasploit 모듈을 분석해 명령어를 추출하고 Caldera ability로 생성하는 플러그인'
address = '/plugin/metasploit/gui'

async def enable(services):
    app = services.get('app_svc').application
    handler = MetasploitHandler(services)
    app.router.add_route('POST', '/plugins/metasploit/search', handler.handle_search)
    app.router.add_route('POST', '/plugins/metasploit/generate', handler.handle_generate)
    app.router.add_route('POST', '/plugins/metasploit/ability', handler.handle_create_ability)
    app.router.add_static('/metasploit', 'plugins/metasploit/static/', append_version=True)

