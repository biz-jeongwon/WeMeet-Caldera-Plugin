# plugins/sliver/hook.py
from plugins.sliver.app.sliver import SliverHandler
from aiohttp import web
import os

name = 'Sliver'
description = 'Sliver implant management plugin for Caldera'
address = '/plugin/sliver/gui'

async def enable(services):
    app = services.get('app_svc').application
    handler = SliverHandler(services)

    app.router.add_static('/sliver', 'plugins/sliver/static/', append_version=True)
    app.router.add_route('GET', '/plugins/sliver/gui', handler.render_page)
    app.router.add_route('GET', '/plugins/sliver/server-status', handler.server_status)
    app.router.add_route('POST', '/plugins/sliver/start-server', handler.start_server)
    app.router.add_route('POST', '/plugins/sliver/generate', handler.handle_generate)
    app.router.add_route('GET', '/plugins/sliver/sessions', handler.list_sessions)
    app.router.add_route('POST', '/plugins/sliver/install-agent', handler.install_agent)
    app.router.add_route('GET', '/plugins/sliver/implants', handler.list_implants)
    app.router.add_route('POST', '/plugins/sliver/delete-implant', handler.delete_implant)
    app.router.add_route('POST', '/plugins/sliver/start-job', handler.start_job)
    app.router.add_route('GET', '/plugins/sliver/jobs', handler.list_jobs)
    app.router.add_route('POST', '/plugins/sliver/delete-listener', handler.delete_job_listener)
    app.router.add_route('POST', '/plugins/sliver/delete-session', handler.delete_session)

    async def download_implant(request):
        filename = request.match_info['filename']
        path = os.path.join(handler.implant_dir, filename)
        if not os.path.exists(path):
            return web.json_response({'error': 'File not found'}, status=404)
        return web.FileResponse(path)

    app.router.add_route('GET', '/downloads/{filename}', download_implant)
