from aiohttp import web

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)    # Yeh health check route define kar rahe hain
async def root_route_handler(request):
    return web.json_response("✅ Bot is alive!")    # Koyeb ko bata rahe hain ki bot alive hai
