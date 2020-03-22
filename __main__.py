from abc import ABC, abstractmethod
from functools import reduce
from enum import Enum, auto
from time import time

from prompt_toolkit import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.filters import renderer_height_is_known, has_focus
from button_replacement import Button
from prompt_toolkit.widgets import (
    Dialog,
    Label,
    TextArea,
    Box,
    Frame
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.containers import (
    Window,
    ConditionalContainer,
    DynamicContainer,
    VSplit,
    HSplit,
    WindowAlign,
    HorizontalAlign,
    VerticalAlign
)
from prompt_toolkit.layout import Layout
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.application.current import get_app
from prompt_toolkit.application import Application


# the target element to focus when switching scenes. if none, equals None.
# this is safe because only one app can run at a time
global__default_target_focus = None


def exit_current_app():
    "Exits the current application, restoring previous terminal state"
    get_app().exit()


def focus_first_element():
    app = get_app()

    # focus first window
    app.layout.focus(next(app.layout.find_all_windows()))

    # focus first ui, eg. button
    app.layout.focus_next()


tab_bindings = KeyBindings()
tab_bindings.add('tab')(focus_next)
tab_bindings.add('s-tab')(focus_previous)

exit_bindings = KeyBindings()
exit_bindings.add('c-c')(lambda e: exit_current_app())


def InputDialog(
    on_ok,
    on_cancel,
    title="",
    prompt="",
    ok_text="OK",
    cancel_text="Cancel",
    is_text_valid=lambda text: True
) -> Dialog:
    """Returns a Dialogue component displaying a text input box"""

    def on_accept(buf):
        if is_text_valid(textfield.text):
            get_app().layout.focus(ok_button)
        return True  # Keep text.

    def on_ok_clicked():
        if is_text_valid(textfield.text):
            on_ok(textfield.text)

    ok_button = Button(text=ok_text, handler=on_ok_clicked)
    exit_button = Button(text=cancel_text, handler=on_cancel)

    textfield = TextArea(multiline=False, accept_handler=on_accept)

    dialog = Dialog(
        title=title,
        body=HSplit(
            [Label(text=prompt, dont_extend_height=True), textfield],
            padding=Dimension(preferred=1, max=1),
        ),
        buttons=[ok_button, exit_button],
        with_background=True
    )

    return dialog


def ToolbarFrame(body, toolbar_content, put_on_top=False):
    if put_on_top:
        return HSplit([toolbar_content, Frame(body)])

    toolbar = ConditionalContainer(
        content=toolbar_content,
        filter=renderer_height_is_known
    )

    return HSplit([Frame(body), toolbar])


class RootScreenType(Enum):
    SET_USERNAME = auto()
    MENU = auto()
    HELP = auto()
    PLAYING = auto()


class UsernameScreenState:
    root_screen_type = RootScreenType.SET_USERNAME


class MenuScreenState:
    root_screen_type = RootScreenType.MENU

    def __init__(self, username):
        self.username = username  # player username


class HelpScreenState:
    root_screen_type = RootScreenType.HELP

    def __init__(self, username, previous_state):
        self.username = username  # player username
        # previous screen (eg. pulling up help while playing;
        self.previous_state = previous_state
        # want to be able to return to previous playing screen)


class PlayingScreenState:
    root_screen_type = RootScreenType.PLAYING

    def __init__(self, username, choice_history, choice_index, start_time):
        self.username = username  # player username
        # history of previous/next game panels/choice panels
        self.choice_history = choice_history
        # incase goes back one choice, so can go forwards again
        self.choice_index = choice_index
        self.start_time = start_time  # time that player started the game


def SetUsernameScreen(controller):
    def is_username_valid(username):
        return len(username) > 0

    def on_username(username):
        new_state = MenuScreenState(username)
        controller.set_state(new_state)

    return InputDialog(
        on_ok=on_username,
        on_cancel=exit_current_app,
        title='We begin...',
        prompt=HTML('<i>What is your name?</i>'),
        cancel_text='Quit',
        is_text_valid=is_username_valid
    )


def create_button_list_kbs(buttons, key_previous, key_next):
    kb = KeyBindings()

    if (len(buttons) > 1):
        is_first_selected = has_focus(buttons[0])
        is_last_selected = has_focus(buttons[-1])

        kb.add(key_previous, filter=~is_first_selected)(focus_previous)
        kb.add(key_next, filter=~is_last_selected)(focus_next)

    return kb


def create_vertical_button_list_kbs(buttons):
    return create_button_list_kbs(buttons, 'up', 'down')


def create_horizontal_button_list_kbs(buttons):
    return create_button_list_kbs(buttons, 'left', 'right')


def MenuScreen(controller):
    def on_start_click():
        new_state = PlayingScreenState(
            username=controller.state.username,
            choice_history=[root_branch],
            choice_index=0,
            start_time=time()
        )
        controller.set_state(new_state)

    def on_help_click():
        new_state = HelpScreenState(
            username=controller.state.username,
            previous_state=controller.state
        )
        controller.set_state(new_state)

    buttons = [
        Button('start', handler=on_start_click),
        Button('help', handler=on_help_click),
        Button('quit', handler=exit_current_app)
    ]

    kb = create_vertical_button_list_kbs(buttons)

    body = Box(
        VSplit([
            HSplit(
                children=buttons,
                padding=Dimension(preferred=1, max=1),
                key_bindings=kb
            )
        ])
    )

    toolbar_content = Window(
        content=FormattedTextControl(
            'Hello %s. I wish you the best of luck...' % controller.state.username
        ),
        align=WindowAlign.CENTER,
        height=1
    )

    return ToolbarFrame(body, toolbar_content)


help_text = '''          88                         
          88                         
          88                         
,adPPYba, 88 ,adPPYYba, 8b       d8  
I8[    "" 88 ""     `Y8 `8b     d8'  
 `"Y8ba,  88 ,adPPPPP88  `8b   d8'   
aa    ]8I 88 88,    ,88   `8b,d8'    
`"YbbdP"' 88 `"8bbdP"Y8     "8"      

This is a choose your own adventure game detailing the russian slav mafia. Each path you choose will lead to more paths, eventually leading to one of five endings. Play at your own risk.

CONTROLS:

Left/Right/Up/Down/Tab/Shift-Tab: Navigate through buttons.

Enter: Click the selected button

Note: You can also click buttons with your mouse

Ctrl-C: Exit
'''


def HelpScreen(controller):
    body = Box(TextArea(help_text, focusable=False, scrollbar=True),
               padding=0, padding_left=1, padding_right=1)

    def on_back_click():
        new_state = controller.state.previous_state
        controller.set_state(new_state)

    buttons = [
        Button('back', handler=on_back_click),
        Button('quit', handler=exit_current_app)
    ]

    kb = create_horizontal_button_list_kbs(buttons)

    toolbar_content = Box(
        VSplit(
            children=buttons,
            align=HorizontalAlign.CENTER,
            padding=Dimension(preferred=10, max=10),
            key_bindings=kb
        ),
        height=1
    )

    return ToolbarFrame(body, toolbar_content)


def get_current_choice(controller):
    return controller.state.choice_history[controller.state.choice_index]


def push_component(controller, component):
    state = controller.state
    new_state = PlayingScreenState(
        username=state.username,
        choice_history=state.choice_history[
            :state.choice_index+1] + [component],
        choice_index=state.choice_index + 1,
        start_time=controller.state.start_time
    )

    controller.set_state(new_state)


class GameComponent(ABC):
    @abstractmethod
    def render(self):
        pass

    def refocus(self):
        pass


class ListChoice(GameComponent):
    def __init__(self, controller, label, choices):
        self._controller = controller
        self._label = label
        self._choices = choices

    def _create_handler(self, sub_component):
        return lambda: push_component(self._controller, sub_component)

    def render(self):
        choices_len = len(self._choices)

        buttons = [
            Button(
                '[%s] %s' % (i, label) if choices_len > 1 else label,
                handler=self._create_handler(sub_component)
            ) for ((label, sub_component), i) in zip(
                self._choices, range(1, choices_len+1))  # this is still a loop even if it is inline..
        ]

        self._first_button = buttons[0]

        global global__default_target_focus
        global__default_target_focus = self._first_button

        kb = create_vertical_button_list_kbs(buttons)

        is_first_selected = has_focus(buttons[0])
        kb.add('up', filter=is_first_selected)(lambda e: focus_first_element())

        return Box(
            HSplit(
                [
                    TextArea(
                        text=self._label.format(
                            name=self._controller.state.username)+'\n',
                        read_only=True,
                        focusable=False,
                        scrollbar=True,
                        # push buttons to bottom of screen
                        height=Dimension(preferred=100000, max=100000)
                    ),
                    HSplit(
                        [
                            VSplit(
                                children=[button],
                                align=HorizontalAlign.CENTER
                            ) for button in buttons
                        ],
                        padding=1,
                        key_bindings=kb
                    )
                ],
                padding=Dimension(preferred=2, max=2),
                width=Dimension(),
                align=VerticalAlign.TOP
            ),
            padding=1
        )

    def refocus(self):
        get_app().layout.focus(self._first_button)


def list_choice(label, choices):
    return lambda controller: ListChoice(controller, label, choices)


def format_time(time_played):
    m, s = divmod(round(time_played), 60)
    h, m = divmod(m, 60)

    return 'Hours: %s, Minutes: %s, Seconds: %s' % (h, m, s)


class EndScreen(GameComponent):
    def __init__(self, controller, label):
        self._controller = controller
        self._label = label

    def render(self):
        current_time = time()
        time_played = current_time - self._controller.state.start_time

        return Box(
            TextArea(
                text=self._label.format(
                    name=self._controller.state.username)+'\n\nTime Played:\n'+format_time(time_played)+'\n',
                read_only=True,
                focusable=False,
                scrollbar=True
            ),
            padding=1
        )


def end_screen(label):
    return lambda controller: EndScreen(controller, label)


stop_squirming_end_screen = end_screen(
    '"Ah. It seems you are smarter then everyone else from today. Good."\n\nВладлен approaches you. He now stands right beside your bed.\n\n"It seems you are still awake! That is great... for me. You see, we, the slav mafia, have been testing this thing... ah yes, this beautiful thing that turns humans... like you... into animals."\n\n"But so far it has only worked on the strong... lucky you! You get to test it! Ah, isn\'t that wonderful!." He picks up a needle from the table beside you, and thrusts it into you. You fall asleep...\n\nA couple hours pass. You wake up, dazed.\n\n"Where am I?" You look around. You\'re surrounded by grass, meters taller than you are. In the distance you hear the sound of bunnies prancing around...\n\n"Oh no..."\n\nIn your back you feel a tracker hidden by a layer of fur. You are stuck in this field forever.'
)

go_for_glory_end_screen = end_screen(
    'You go for glory. You violently thrust your hands upwards, absolutely destroying the handcuffs. A wave of confidence rushes over you. You can do this! You reach for the mallet. The slav punches you in your face, fracturing your skull, immediately knocking you out. You never wake up'
)

root_branch = list_choice(
    'You slowly wake up. "Hello {name}..." you hear in the distance. "You can call me Владлен."',
    [
        (
            '"Who?"',
            list_choice(
                '"Ah yes. I forgot. Your an ignorant Australian. You have never been in Russia. Until now. And who am I? I am doctor Владлен..."\n\nYou feel weak. You struggle to stay awake.',
                [
                    (
                        'Get up. Try to fight this man',
                        list_choice(
                            'You try to lift yourself up. But you can\'t move! You\'re eyeseight strengthens, and you look around. Everything\'s white...\n\n"What?..." you think, confused.\n\nYou\'re body tenses... you regain movement, but you still can\'t feel your hands or legs. You see that you are on a hospital bed, but you can\'t be sure... Владлен is standing to your right.',
                            [
                                (
                                    'Keep squirming. Try to get out of here',
                                    list_choice(
                                        'You\'re arms and legs are numb. You violently throw your body left and right. The bed underneath you shakes...\n\n"You FOOL! You think you can escape? Think again!" Владлен laughs russian style...\n\nYou\'re eyes clear up and you get a good glimpse of him. He looks exactly like you thought he would look like:\n    Bald head,\n    Tattoos all over his hairy chest,\n    Muscles bigger than you\'re entire body.\n\nHe is squatting at you, both him and his adidas tracksuit are glaring straight into your eyes. You\'re worst nightmare has come to light...\n\nYOU HAVE BEEN CAPTURED BY A SLAV!',
                                        [
                                            (
                                                'Keep squirming. More violent',
                                                list_choice(
                                                    'You\'re arms are still numb. It\'s still useless. But nevertheless you thrust your body left and right, more violently. It is to no avail...\n\n"I admire you\'re effort. But you must realise you\'re never getting out of here... I will be back in an hour or so"\n\nВладлен walks towards the door, laughing like a madman. As he exits, another slav enters the room. His adidas tracksuit is even more daunting than Владлен\'s. He stares straight at you.',
                                                    [
                                                        (
                                                            'Look around. There\'s got to be something that can help you',
                                                            list_choice(
                                                                'Blood rushes to your hands. You can finally feel them! And move them!\n\nYou look at your hands. They are handcuffed to the table. You wiggle them slightly...\n\nThe handcuffs are loose! You\'re sure that if you give it enough force they will snap.\n\nYou\'re heart races... You have a chance to escape! You take in your surroundings. There is a door on the wall in front of you. Maybe it\'s an exit? You look around. To you\'re right, on the table next to your bed, there is a mallet. Just as you\'re about to go for glory, fear engulfs you as you\'re reminded of the slav staring into you\'re soul.',
                                                                [
                                                                    (
                                                                        'Go for Glory! Try to escape right now!',
                                                                        go_for_glory_end_screen
                                                                    ),
                                                                    (
                                                                        'Too risky. Wait for another opportunity...',
                                                                        list_choice(
                                                                            'You decide to wait for another opportunity. 5 minutes pass... Nothing changes. The slav is still staring straight into your soul. Creepy. Also scary, very scary\n\n10 minutes pass... Nothing.',
                                                                            [
                                                                                (
                                                                                    'It\'s now or never. Go for glory!',
                                                                                    go_for_glory_end_screen
                                                                                ),
                                                                                (
                                                                                    'Wait for another opportunity... Who knows',
                                                                                    list_choice(
                                                                                        'You\'re basic freeze instincts have kicked in...\nAfter an hour of excruciating waiting... The slav whimpers... "My bladder!"\n\nHe swiftly leaves out the door, holding his crotch.',
                                                                                        [
                                                                                            (
                                                                                                'This is your chance. Escape!',
                                                                                                list_choice(
                                                                                                    'You thrust you\'re hands free from the handcuffs. Blood rushes through your body. You stand up...\n\nInstinctively, you grab the mallet and hold it in an offensive position, ready to strike. You tippy toe out towards the door. The door is locked...\n\nSmash! You absolutely obliterate the lock with your hammer. The door swings open. On the outwards facing side of the door you notice a label, "Test Subject #198: {name}"\n\nYou don\'t have time to think. You exit the door, into a corridor stretching left and right. You hear footsteps approaching from around the corner, but you don\'t know which side it\'s coming from!\n\n"Should I go left or right?" you think to yourself.',
                                                                                                    [
                                                                                                        (
                                                                                                            'Go left.',
                                                                                                            end_screen(
                                                                                                                'You go left. The footsteps become louder. They approach faster. You start sprinting... faster... faster... the footsteps fade away. You reach a door labelled "Laboratory Exit."\n\nYou open the door. Sunshine! You are free...\n\nYou sprint into the distance, with no idea where you are. You run for days on end, driven by pure fear. You reach several russian villages, all of which are empty. How they are empty, you don\'t know, but you keep running, feeding on the food you find from each village. Eventually you reach the shore. Miraculously, there is a fishing boat waiting for you.\n\n"Weird," you think to yourself, "There\'s no one anywhere..." You get in the boat and row for what seems like an eternity before you eventually reach land. A small island.\n\nYou get off the boat, and step out onto the shore...\n\nYou pass out...\n\nHours pass...\n\nWhen you wake up, your boat is gone. Your are stuck on this island, forced to live off of coconuts and fish for the rest of your life. That is, if you don\'t go insane first...'
                                                                                                            )
                                                                                                        ),
                                                                                                        (
                                                                                                            'Go right',
                                                                                                            end_screen(
                                                                                                                'You go right. The footsteps become louder...\n\nВладлен and his fellow slav turn towards you. You\'re eyes meet. They start sprinting towards you. Only now can you grasp their true size.\n\n"They must be 7 feet each..." you think to yourself. They\'re muscles are huge... Pure terror envelops your mind. Then you stare into their adidas trackpants and realise the enormity of the situation. You are screwed. They sprint faster towards you, their anger and speed increasing every second... You instinctively whimper, before falling into a slump on the ground, passed out from pure terror. You never wake up...')
                                                                                                        )
                                                                                                    ]
                                                                                                )
                                                                                            )
                                                                                        ]
                                                                                    )
                                                                                )
                                                                            ]
                                                                        )
                                                                    )
                                                                ]
                                                            )
                                                        )
                                                    ]
                                                ),
                                            ),
                                            (
                                                'Stop squirming. It\'s no use. Give up.',
                                                stop_squirming_end_screen
                                            )
                                        ]
                                    )
                                ),
                                (
                                    'Stop moving. See what he has to say',
                                    stop_squirming_end_screen
                                )
                            ]
                        )
                    ),
                    (
                        'Go back to sleep. Everything will be alright, right?',
                        end_screen(
                            'Your vision weakens. Everything goes dark. Five hours pass. You wake up, but your thoughts come slower than usual. You look around. Nothing. You can\'t see anthing... Suddenly, you feel a sharp needle pierce your neck, and in the distance hear several men laughing in evil Russian accents. You pass out, never to wake again.'
                        )
                    )
                ]
            )
        )
    ]
)


def PlayingScreen(controller):
    current_component = get_current_choice(controller)
    component = current_component(controller)
    body = component.render()
    username = controller.state.username
    choice_history = controller.state.choice_history
    choice_index = controller.state.choice_index

    def on_back_click():
        new_state = PlayingScreenState(
            username=username,
            choice_history=choice_history,
            choice_index=choice_index-1,
            start_time=controller.state.start_time
        )
        controller.set_state(new_state)

    def on_help_click():
        new_state = HelpScreenState(
            username=username,
            previous_state=controller.state
        )
        controller.set_state(new_state)

    def on_menu_click():
        new_state = MenuScreenState(username)
        controller.set_state(new_state)

    def on_next_click():
        new_state = PlayingScreenState(
            username=username,
            choice_history=choice_history,
            choice_index=choice_index+1,
            start_time=controller.state.start_time
        )
        controller.set_state(new_state)

    buttons = [
        Button('help', handler=on_help_click),
        Button('menu', handler=on_menu_click),
        Button('quit', handler=exit_current_app)
    ]

    if choice_index > 0:
        buttons.insert(
            0, Button('(back)', handler=on_back_click))

    if choice_index < len(choice_history) - 1:
        buttons.append(Button('(next)', handler=on_next_click))

    kb = create_horizontal_button_list_kbs(buttons)

    is_button_focused = reduce(lambda a, b: a | b, map(has_focus, buttons))

    def reset_focus(_):
        component.refocus()

    kb.add('down', filter=is_button_focused)(reset_focus)

    toolbar_content = Box(
        VSplit(
            children=buttons,
            align=HorizontalAlign.CENTER,
            key_bindings=kb
        ),
        height=1
    )

    return ToolbarFrame(body, toolbar_content, put_on_top=True)


def RootScreen(controller):
    state = controller.state

    if state.root_screen_type == RootScreenType.SET_USERNAME:
        return SetUsernameScreen(controller)

    if state.root_screen_type == RootScreenType.MENU:
        return MenuScreen(controller)

    if state.root_screen_type == RootScreenType.HELP:
        return HelpScreen(controller)

    if state.root_screen_type == RootScreenType.PLAYING:
        return PlayingScreen(controller)


class Controller:
    def __init__(self, state, Screen):
        self._Screen = Screen
        self._container = DynamicContainer(lambda: self._current_screen)
        self.set_state(state)

    def set_state(self, new_state):
        self.state = new_state
        self._current_screen = self._Screen(self)

    def __pt_container__(self):
        return self._container


def RootController(root_state=UsernameScreenState()):
    return Controller(root_state, RootScreen)


root_style = Style.from_dict({
    'dialog': 'noinherit',
    'dialog frame.label': 'noinherit',
    'dialog.body': 'noinherit',
    'dialog shadow': 'noinherit',
    'dialog.body text-area': 'noinherit',
    'button.focused': '#000000 bg:#ffffff'
})


def build_application():
    layout = Layout(RootController())

    def ensure_focus(_):
        """Ensures that at least one element on the screen is focused"""
        app = get_app()

        # prompt_toolkit's implementation of focusing is retarded
        # so this is the only way I found of 'making it work'

        # when switching screens or something prompt_toolkit doesn't recognize
        # the new focusable elements added to the screen. this will ensure
        # that at least one container/ui is marked as focusable so
        # the screen can be interacted with

        global global__default_target_focus  # preferred element to be focused

        if global__default_target_focus:
            app.layout.focus(global__default_target_focus)
            global__default_target_focus = None  # reset for next render

            app.invalidate()  # trigger re-render
        elif len(app.layout.get_visible_focusable_windows()) == 0:
            focus_first_element()

            app.invalidate()  # trigger re-render

    return Application(
        layout=layout,
        key_bindings=merge_key_bindings([tab_bindings, exit_bindings]),
        full_screen=True,
        mouse_support=True,
        after_render=ensure_focus,
        style=root_style
    )


def main():
    build_application().run()


if __name__ == "__main__":
    main()
