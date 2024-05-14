# `perspective-python` Remote Session Example

A simple example of a `perspective-python` server which can virtually host
unique session-scoped data via an RPC side channel.

It works like this. First, enter a file path to an Apache Arrow file in the
`<input>` box relative to the server's working directory. The server will
receive this command via a dedicated `WebSocket` handler, which loads the file
from disk and hosts it in the global `PerspectiveManager` under a random name,
returning the new name to the Browser via the same side channel `WebSocket`.

Next, the client receives this name and calls `Client.open_table()` , creating a
virtual `Table` connection to the data loaded for that browser session, which
can be passed directly to `HTMLPerspectiveViewer.load()`.

Finally, when the RPC `Websocket` closes, the `on_close()` handler deletes the
`Table` created for the session.
