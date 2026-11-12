from drafter import *
from dataclasses import dataclass, field
from bakery import assert_equal
from PIL import Image
from typing import Optional
import numpy as np
import random
import io



# DATA CLASSES


@dataclass
class ImageInfo:
    current_img: Optional[Image]
    associated_code: str


@dataclass
class HistoryEntry:
    action: str
    method: str
    details: str
    code: str


@dataclass
class State:
    file: ImageInfo
    displayed_text: str
    action: str
    current_method: str
    history: list[HistoryEntry] = field(default_factory=list)
    total_operations: int = 0



# MESSAGE CONVERSION FUNCTIONS


def message_to_binary(message: str) -> str:
    binary = ''

    for byte in message.encode('utf-8'):
        binary += format(byte, '08b')

    return binary


assert_equal(
    message_to_binary('hello'),
    '0110100001100101011011000110110001101111'
)

assert_equal(message_to_binary(''), '')

assert_equal(
    message_to_binary('one two'),
    '01101111011011100110010100100000011101000111011101101111'
)


def binary_to_message(binary: str) -> str:
    message_bytes = bytearray()

    for i in range(0, len(binary), 8):
        byte = binary[i:i + 8]

        if len(byte) == 8:
            message_bytes.append(int(byte, 2))

    return message_bytes.decode('utf-8', errors='replace')


assert_equal(
    binary_to_message(
        '0110100001100101011011000110110001101111'
    ),
    'hello'
)

assert_equal(binary_to_message(''), '')

assert_equal(
    binary_to_message(
        '01101111011011100110010100100000011101000111011101101111'
    ),
    'one two'
)



# ENCODING FUNCTION


def encode(state: State, im: Image, message: str,
           method: str) -> State:

    state.action = "encode"
    state.current_method = method
    state.file.current_img = im

    binary = message_to_binary(message)

    # Convert image into a standard RGB format.
    opened_img = im.convert('RGB')
    img_array = np.asarray(opened_img).copy()

    height, width, channels = img_array.shape

    # Determine which color channel to use.
    channel = int(method[-1]) - 1

    # Check whether the image can hold the message.
    if len(binary) > width * height:
        state.displayed_text = (
            'ERROR: Your image is not large enough '
            'to encode this message!'
        )
        return state

    # Encode one binary digit into each pixel.
    for i, bit in enumerate(binary):

        y = i // width
        x = i % width

        current_color = img_array[y, x, channel]

        # Change the least significant bit.
        img_array[y, x, channel] = (
            (int(current_color) & 254) | int(bit)
        )

    # Recreate the encoded image.
    final_im = Image.fromarray(img_array)

    state.file.current_img = final_im

    # Generate the associated decoding code.
    code = (
        str(random.randint(1000, 9999))
        + method[-1]
        + str(len(binary))
        + str(random.randint(1000, 9999))
    )

    state.file.associated_code = code

    state.displayed_text = (
        'Your image has been successfully encoded!'
    )

    # Add this operation to the history list.
    state.history.append(
        HistoryEntry(
            'Encoding',
            method,
            str(len(message)) + ' characters',
            code
        )
    )

    state.total_operations += 1

    return state



# DECODING FUNCTION


def decode(state: State, im: Image, code: str) -> State:

    state.action = "decode"
    state.file.current_img = im
    state.file.associated_code = code

    # Validate the code format.
    if len(code) < 10 or not code.isdigit():
        state.displayed_text = (
            'ERROR: The code provided is not valid!'
        )
        return state

    method_number = int(code[4])
    state.current_method = 'Method ' + str(method_number)

    if method_number not in [1, 2, 3]:
        state.displayed_text = (
            'ERROR: The encoding method is invalid!'
        )
        return state

    message_length = int(code[5:-4])

    if message_length % 8 != 0:
        state.displayed_text = (
            'ERROR: The code contains an invalid message length!'
        )
        return state

    # Convert the image into RGB.
    opened_img = im.convert('RGB')
    img_array = np.asarray(opened_img)

    height, width, channels = img_array.shape

    if message_length > width * height:
        state.displayed_text = (
            'ERROR: The code is not valid for this image!'
        )
        return state

    channel = method_number - 1

    # Extract the binary message.
    found_message_binary = ''

    for i in range(message_length):

        y = i // width
        x = i % width

        pixel_value = int(img_array[y, x, channel])

        if pixel_value % 2 == 0:
            found_message_binary += '0'
        else:
            found_message_binary += '1'

    # Convert the binary message back into text.
    decoded_message = binary_to_message(found_message_binary)

    state.displayed_text = decoded_message

    # Add decoding operation to history.
    state.history.append(
        HistoryEntry(
            'Decoding',
            state.current_method,
            str(len(decoded_message)) + ' characters',
            code
        )
    )

    state.total_operations += 1

    return state



# HOME PAGE


@route
def index(state: State) -> Page:

    state.displayed_text = (
        ''
        'Hide secret messages inside images '
        'and retrieve them whenever you want.'
    )

    return Page(state, [
        Header("🦕 Steganography"),
        state.displayed_text,
        '\n',
        Button('Encode a Message', 'encoding'),
        Button('Decode a Message', 'decoding'),
        Button('About', 'about_page'),
        Button('Operation History', 'history_page'),
        Button('Help', 'help_page')
    ])



# ABOUT PAGE


@route
def about_page(state: State) -> Page:

    state.displayed_text = (
        'Steganography is the practice of hiding '
        'information inside another file. '
        'This website uses the least significant bit '
        'method to hide messages inside images.'
    )

    return Page(state, [
        Header('About Steganography'),
        state.displayed_text,
        '\n',
        'Encoding: A message is converted into binary '
        'and stored in the image pixels.',
        '\n',
        'Decoding: The binary digits are extracted '
        'and converted back into a readable message.',
        '\n',
        Button('Return Home', 'index')
    ])



# ENCODING PAGE


@route
def encoding(state: State) -> Page:

    state.action = 'encode'
    state.displayed_text = (
        'Upload an image, enter your secret message, '
        'and select an encoding method.'
    )

    return Page(state, [
        Header('Encode a Message'),
        state.displayed_text,
        '\n',
        'Upload your PNG image:',
        FileUpload('im', accept='.png'),
        '\n',
        'Enter the message you want to hide:',
        TextBox('message'),
        '\n',
        'Choose an encoding method:',
        SelectBox(
            'method',
            ['Method 1', 'Method 2', 'Method 3']
        ),
        '\n',
        Button('Encode Message', 'completed_encode'),
        Button('Return Home', 'index')
    ])



# DECODING PAGE


@route
def decoding(state: State) -> Page:

    state.action = 'decode'
    state.displayed_text = (
        'Upload an encoded image and enter the '
        'associated code to reveal your message.'
    )

    return Page(state, [
        Header('Decode a Message'),
        state.displayed_text,
        '\n',
        'Upload your encoded PNG image:',
        FileUpload('im', accept='.png'),
        '\n',
        'Enter your associated decoding code:',
        TextBox('code'),
        '\n',
        Button('Decode Message', 'completed_decode'),
        Button('Return Home', 'index')
    ])



# COMPLETED ENCODING PAGE


@route
def completed_encode(
    state: State,
    im: bytes,
    message: str,
    method: str
) -> Page:

    state.action = 'encode'
    state.current_method = method

    try:
        im2 = Image.open(io.BytesIO(im))
        im2.load()

        state = encode(state, im2, message, method)

    except Exception:
        state.displayed_text = (
            'ERROR: The uploaded image could not be opened.'
        )

        return error_page(state)

    if state.displayed_text.startswith('ERROR'):
        return error_page(state)

    return Page(state, [
        Header('Encoding Successful!'),
        state.displayed_text,
        '\n',
        'Your associated decoding code is:',
        state.file.associated_code,
        '\n',
        'Save this code because you will need it '
        'to decode your image.',
        '\n',
        'Download your encoded image:',
        Download(
            'download',
            'encoded_img.png',
            Picture.from_pil(state.file.current_img)
        ),
        '\n',
        Button('Encode Another Message', 'encoding'),
        Button('Return Home', 'index')
    ])



# COMPLETED DECODING PAGE


@route
def completed_decode(
    state: State,
    im: bytes,
    code: str
) -> Page:

    state.action = 'decode'

    try:
        im2 = Image.open(io.BytesIO(im))
        im2.load()

        state = decode(state, im2, code)

    except Exception:
        state.displayed_text = (
            'ERROR: The uploaded image could not be opened.'
        )

        return error_page(state)

    if state.displayed_text.startswith('ERROR'):
        return error_page(state)

    return Page(state, [
        Header('Decoding Successful!'),
        'Your decoded message is:',
        '\n',
        state.displayed_text,
        '\n',
        Button('Decode Another Message', 'decoding'),
        Button('Return Home', 'index')
    ])



# HISTORY PAGE


@route
def history_page(state: State) -> Page:

    state.displayed_text = (
        'Here you can view your previous encoding '
        'and decoding operations.'
    )

    content = [
        Header('Operation History'),
        state.displayed_text,
        '\n',
        'Total operations: ' + str(state.total_operations),
        '\n'
    ]

    # Iterate through the list of HistoryEntry objects.
    for entry in state.history:

        content.append(
            entry.action
            + ' | '
            + entry.method
            + ' | '
            + entry.details
            + ' | Code: '
            + entry.code
        )

        content.append('\n')

    if len(state.history) == 0:
        content.append('No operations have been completed yet.')

    content.append(Button('Clear History', 'clear_history'))
    content.append(Button('Return Home', 'index'))

    return Page(state, content)



# CLEAR HISTORY PAGE


@route
def clear_history(state: State) -> Page:

    state.history.clear()
    state.total_operations = 0

    state.displayed_text = (
        'Your operation history has been cleared.'
    )

    return Page(state, [
        Header('History Cleared'),
        state.displayed_text,
        '\n',
        Button('Return to History', 'history_page'),
        Button('Return Home', 'index')
    ])



# HELP PAGE


@route
def help_page(state: State) -> Page:

    state.displayed_text = (
        'Follow the instructions below to use '
        'the steganography website.'
    )

    return Page(state, [
        Header('How to Use the Website'),
        state.displayed_text,
        '\n',
        '1. Select Encode a Message to hide text.',
        '\n',
        '2. Upload a PNG image.',
        '\n',
        '3. Enter the message you want to hide.',
        '\n',
        '4. Select one of the three encoding methods.',
        '\n',
        '5. Download the encoded image and save its code.',
        '\n',
        '6. Select Decode a Message to retrieve your text.',
        '\n',
        '7. Upload the encoded image and enter its code.',
        '\n',
        Button('Return Home', 'index')
    ])



# ERROR PAGE


@route
def error_page(state: State) -> Page:

    state.displayed_text = state.displayed_text

    return Page(state, [
        Header('Something Went Wrong'),
        state.displayed_text,
        '\n',
        'Please check your inputs and try again.',
        '\n',
        Button('Try Encoding Again', 'encoding'),
        Button('Try Decoding Again', 'decoding'),
        Button('Return Home', 'index')
    ])



# START SERVER


start_server(
    State(
        ImageInfo(None, ''),
        '',
        '',
        ''
    )
)
