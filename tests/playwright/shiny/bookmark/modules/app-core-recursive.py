import os
from typing import Literal

from starlette.requests import Request

from shiny import App, Inputs, Outputs, Session, module, reactive, render, ui
from shiny.bookmark import BookmarkState
from shiny.bookmark._restore_state import RestoreState


@module.ui
def mod_btn(idx: int = 1):
    return ui.TagList(
        ui.h3(f"Module {idx}"),
        ui.layout_column_wrap(
            ui.TagList(
                ui.input_radio_buttons(
                    "btn1", "Button Input", choices=["a", "b", "c"], selected="a"
                ),
                ui.input_radio_buttons(
                    "btn2",
                    "Button Value",
                    choices=["a", "b", "c"],
                    selected="a",
                ),
            ),
            ui.output_ui("ui_html"),
            ui.output_code("value"),
            width="200px",
        ),
        ui.hr(),
        mod_btn(f"sub{idx}", idx - 1) if idx > 0 else None,
    )


@module.server
def btn_server(input: Inputs, output: Outputs, session: Session, idx: int = 1):

    @render.ui
    def ui_html():
        return ui.TagList(
            ui.input_radio_buttons(
                "dyn1", "Dynamic Input", choices=["a", "b", "c"], selected="a"
            ),
            ui.input_radio_buttons(
                "dyn2", "Dynamic Value", choices=["a", "b", "c"], selected="a"
            ),
        )

    @render.code
    def value():
        value_arr = [input.btn1(), input.btn2(), input.dyn1(), input.dyn2()]
        return f"{value_arr}"

    @reactive.effect
    @reactive.event(input.btn1, input.btn2, input.dyn1, input.dyn2, ignore_init=True)
    async def _():
        # print("app-Bookmarking!")
        await session.bookmark()

    session.bookmark.exclude.append("btn2")
    session.bookmark.exclude.append("dyn2")

    @session.bookmark.on_bookmark
    def _(state: BookmarkState) -> None:
        state.values["btn2"] = input.btn2()
        state.values["dyn2"] = input.dyn2()

    @session.bookmark.on_restore
    def _(restore_state: RestoreState) -> None:
        # print("app-Restore state:", restore_state.values)

        if "btn2" in restore_state.values:

            ui.update_radio_buttons("btn2", selected=restore_state.values["btn2"])

        if "dyn2" in restore_state.values:

            ui.update_radio_buttons("dyn2", selected=restore_state.values["dyn2"])

    if idx > 0:
        btn_server(f"sub{idx}", idx - 1)


k = 2


def app_ui(request: Request) -> ui.Tag:
    # print("app-Making UI")
    return ui.page_fixed(
        ui.output_code("bookmark_store"),
        "Click Buttons to update bookmark",
        mod_btn(f"mod{k - 1}", k - 1),
    )


# Needs access to the restore context to the dynamic UI
def server(input: Inputs, output: Outputs, session: Session):

    btn_server(f"mod{k - 1}", k - 1)

    @render.code
    def bookmark_store():
        return f"{session.bookmark.store}"

    @session.bookmark.on_bookmark
    async def on_bookmark(state: BookmarkState) -> None:
        print(
            "app-On Bookmark",
            "\nInputs: ",
            await state.input._serialize(exclude=state.exclude, state_dir=None),
            "\nValues: ",
            state.values,
            "\n\n",
        )
        # session.bookmark.update_query_string()

        pass

    session.bookmark.on_bookmarked(session.bookmark.update_query_string)
    # session.bookmark.on_bookmarked(session.bookmark.show_modal)


SHINY_BOOKMARK_STORE: Literal["url", "server"] = os.getenv(
    "SHINY_BOOKMARK_STORE", "url"
)  # pyright: ignore[reportAssignmentType]
if SHINY_BOOKMARK_STORE not in ["url", "server"]:
    raise ValueError("SHINY_BOOKMARK_STORE must be either 'url' or 'server'")
app = App(app_ui, server, bookmark_store=SHINY_BOOKMARK_STORE, debug=False)
