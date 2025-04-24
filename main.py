from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routes.auth import auth_tok
from dotenv import load_dotenv
from routes.auth import rolebasedacess
from routes.admin_function import role_management
from routes.ordersystem import orderplacesystem
from routes.menu_manage import menu_management, menu_filter
from routes.image_upload import image_up
from routes.admin_function import discount_management
from routes.admin_function import discount_calculation
from routes.admin_function.discount_calculation import update_discounted_prices
from routes.scan_and_dine import qr_management
from routes.ordersystem import billing_system
from routes.bill_format import Bill_template
from routes.bill_format import Bill_Generation
from routes.bill_format import Bill_template
from routes.bill_format import feedback_form
from fastapi.staticfiles import StaticFiles
from routes.table_management import table_management
from routes.client_intelligence import routes
from routes.customer_management import customer_management_routes
from routes.item_analytics import item_analytics_router
from routes.campaign import customer_segment_routes
from routes.campaign.sending_campaign.routes import email_campaign_routes
from routes.campaign.sending_campaign.routes import email_template_routes




app = FastAPI()
# origins = ["https://wookraft.netlify.app/"]
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(menu_management.router, prefix="/menu", tags=["MENU"])
app.include_router(image_up.router, prefix="/image_up", tags=["IMAGE_UPLOAD"])
app.include_router(menu_filter.router, prefix="/menu/sort", tags=["MENU_FILTER"])
app.include_router(auth_tok.authRouter, prefix="/auth_tok", tags=["AUTH_TOKEN"])
app.include_router(rolebasedacess.adminRouter, prefix="/admin", tags=["ADMIN"])
app.include_router(role_management.router, prefix="/admin", tags=["ADMIN"])
app.include_router(orderplacesystem.router, prefix="/ordersystem", tags=["ORDER_SYSTEM"])
app.include_router(discount_management.router, prefix="/discount", tags=["ADMIN"])
# app.include_router(discount_calculation.router, prefix="/discount_calculation", tags=["ADMIN"])
app.include_router(qr_management.router, prefix="/qr", tags=["QR_GENERATOR"])
app.include_router(billing_system.router, prefix="/billing", tags=["BILLING_SYSTEM"])
# app.include_router(Bill_template.router, prefix="/billing_template/templates", tags=["Bill Templates"])
# app.include_router(Bill_Generation.router, prefix="/billing_generation", tags=["Bill Generation"])
app.include_router(Bill_template.router, prefix="/billing_template", tags=["Bill Templates"])
app.include_router(feedback_form.router,  tags=["Feedback Form"])
app.include_router(table_management.router, prefix="/tables_management", tags=["Table Management"])
app.include_router(routes.router, prefix="/chart", tags=["Client Intelligence"])
app.include_router(customer_management_routes.router, prefix="/customer_management", tags=["Customer Management"])
app.include_router(item_analytics_router.router, prefix="/item_analytics", tags=["Item Analytics"])
app.include_router(customer_segment_routes.router, prefix="/customer_segments", tags=["Customer Segments"])
app.include_router(email_campaign_routes.router, prefix="/email_campaign", tags=["Email Campaign"])
app.include_router(email_template_routes.router, prefix="/email_template" \
"", tags=["Email Template"])
# app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/static", StaticFiles(directory="C:/Users/adity/Desktop/WooAdmin/admizn/src"), name="static")



app.websocket("/ws/waiter/{employee_id}")(orderplacesystem.websocket_endpoint_waiter)
app.websocket("/ws/kds")(orderplacesystem.websocket_endpoint_kds)
app.websocket("/ws/tables/{client_id}")(table_management.websocket_endpoint)



# @app.on_event("startup")
# async def startup_event():
#     print("Starting up...")
#     try:
#         # discount_calculation.listen_for_coupon_changes()
#         discount_calculation.schedule_coupon_tasks()
#         print("Startup tasks completed.")
#     except Exception as e:
#         print(f"Error during startup: {e}")

# @app.get("/trigger_discount_update")
# async def trigger_discount_update():
#     """Manually trigger discount update."""
#     task = update_discounted_prices.apply_async()
#     return {"message": "Discount update triggered", "task_id": task.id}





# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=8000)



# for tablet
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)