import reflex as rx
from components.navbar import navbar
from components.hero import hero
from components.footer import footer

def index() -> rx.Component:
    return rx.vstack(
        navbar(),
        hero(),
        rx.box(
            rx.text_area(
                id="editor",
                placeholder="Paste Python code here...",
                width="100%",
                height="200px",
                background="#f9f9f9",
            ),
            rx.button("Review My Code", color_scheme="blue"),
            padding="2em",
            width="100%",
        ),
        footer(),
        spacing="4",
        align="center",
    )

app = rx.App()
app.add_page(index)
