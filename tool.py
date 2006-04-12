"""Tools are used to add interactive behavior to a View.

Tools can either not act on an event (None), just handle the event
(HANDLED) or grab the event and all successive events until the tool is done
(GRAB, UNGRAB; e.g. on a button press/release).

The tools in this module are made to work properly in a ToolChain.

Current tools:
    ToolChain - for chaining individual tools together.
    HoverTool - make the item under the mouse cursor the "hovered item"
    ItemTool - handle selection and movement of items
    HandleTool - handle selection and movement of handles

Required:
    PlacementTool - for placing items on the canvas
    RubberBandTool - for Rubber band selection

Maybe even:
    TextEditTool - for editing text on canvas items (that support it)
    
"""

import cairo
import gtk

DEBUG_TOOL = False

HANDLED = 1
GRAB = 2
UNGRAB = 3

class Tool(object):

    def __init__(self):
        pass

    def on_button_press(self, view, event):
        """Mouse (pointer) button click. A button press is normally followed by
        a button release. Double and triple clicks should work together with
        the button methods.

        A single click is emited as:
                on_button_press
                on_button_release

        In case of a double click:
                single click +
                on_button_press
                on_double_click
                on_button_release

        In case of a tripple click:
                double click +
                on_button_press
                on_triple_click
                on_button_release
        """
        if DEBUG_TOOL: print 'on_button_press', view, event

    def on_button_release(self, view, event):
        """Button release event, that follows on a button press event.
        Not that double and tripple clicks'...
        """
        if DEBUG_TOOL: print 'on_button_release', view, event
        pass

    def on_double_click(self, view, event):
        """Event emited when the user does a double click (click-click)
        on the View.
        """
        if DEBUG_TOOL: print 'on_double_click', view, event
        pass

    def on_triple_click(self, view, event):
        """Event emited when the user does a triple click (click-click-click)
        on the View.
        """
        if DEBUG_TOOL: print 'on_triple_click', view, event
        pass

    def on_motion_notify(self, view, event):
        """Mouse (pointer) is moved.
        """
        if DEBUG_TOOL: print 'on_motion_notify', view, event
        pass

    def on_key_press(self, view, event):
        """Keyboard key is pressed.
        """
        if DEBUG_TOOL: print 'on_key_press', view, event
        pass

    def on_key_release(self, view, event):
        """Keyboard key is released again (follows a key press normally).
        """
        if DEBUG_TOOL: print 'on_key_release', view, event
        pass


class ToolChain(Tool):
    """A ToolChain can be used to chain tools together, for example HoverTool,
    HandleTool, SelectionTool.
    """

    def __init__(self):
        self._tools = []
        self._grabbed_tool = None

    def append(self, tool):
        self._tools.append(tool)

    def prepend(self, tool):
        self._tools.insert(0, tool)

    def _handle(self, func, view, event):
        """Handle the event by calling each tool until the event is handled
        or grabbed.
        """
        if self._grabbed_tool:
            if getattr(self._grabbed_tool, func)(view, event) in (UNGRAB, None):
                if DEBUG_TOOL: print 'UNgrab tool', self._grabbed_tool
                self._grabbed_tool = None
        else:
            for tool in self._tools:
                rt = getattr(tool, func)(view, event)
                if rt == GRAB:
                    if DEBUG_TOOL: print 'Grab tool', tool
                    self._grabbed_tool = tool
                if rt in (HANDLED, GRAB):
                    return rt
        
    def on_button_press(self, view, event):
        self._handle('on_button_press', view, event)

    def on_button_release(self, view, event):
        self._handle('on_button_release', view, event)

    def on_double_click(self, view, event):
        self._handle('on_double_click', view, event)

    def on_triple_click(self, view, event):
        self._handle('on_triple_click', view, event)

    def on_motion_notify(self, view, event):
        self._handle('on_motion_notify', view, event)

    def on_key_press(self, view, event):
        self._handle('on_key_press', view, event)

    def on_key_release(self, view, event):
        self._handle('on_key_release', view, event)


class HoverTool(Tool):
    """Make the item under the mouse cursor the "hovered item".
    """
    
    def __init__(self):
        pass

    def on_motion_notify(self, view, event):
        old_hovered = view.hovered_item
        view.hovered_item = view.get_item_at_point(event.x, event.y)
        return True


class ItemTool(Tool):
    """ItemTool does selection and dragging of items. On a button click,
    the currently "hovered item" is selected. If CTRL or SHIFT are pressed,
    already selected items remain selected. The last selected item gets the
    focus (e.g. receives key press events).
    """

    def __init__(self):
        self.last_x = 0
        self.last_y = 0

    def on_button_press(self, view, event):
        self.last_x, self.last_y = event.x, event.y
        # Deselect all items unless CTRL or SHIFT is pressed
        # or the item is already selected.
        if not (event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK)
                or view.hovered_item in view.selected_items):
            del view.selected_items
        if view.hovered_item:
            view.focused_item = view.hovered_item
        return GRAB

    def on_button_release(self, view, event):
        return UNGRAB

    def on_motion_notify(self, view, event):
        """Normally, just check which item is under the mouse pointer
        and make it the view.hovered_item.
        """
        if event.state & gtk.gdk.BUTTON_PRESS_MASK:
            # Move selected items

            # First request redraws for all items, before enything is
            # changed.
            for i in view.selected_items:
                # Set a redraw request before the item is updated
                view.queue_draw_item(i, handles=True)

            # Now do the actual moving.
            for i in view.selected_items:
                # Do not move subitems of selected items
                anc = set(view.canvas.get_ancestors(i))
                if anc.intersection(view.selected_items):
                    continue

                # Calculate the distance the item has to be moved
                dx, dy = event.x - self.last_x, event.y - self.last_y
                # Move the item and schedule it for an update
                i.matrix.translate(*i._matrix_w2i.transform_distance(dx, dy))
                i.request_update()
                i.canvas.update_matrices()
                b = i._view_bounds
                view.queue_draw_item(i, handles=True)
                view.queue_draw_area(b[0] + dx, b[1] + dy, b[2] - b[0], b[3] - b[1])
            self.last_x, self.last_y = event.x, event.y
            return GRAB
        return HANDLED


class HandleTool(Tool):

    def __init__(self):
        pass

    def on_button_press(self, view, event):
        for item in reversed(view.canvas.get_all_items()):
            x, y = item._matrix_w2i.transform_point(event.x, event.y)
            print event.x, event.y, x, y
            for h in item.handles():
                if abs(x - h.x) < 5 and abs(y - h.y) < 5:
                    self._grabbed_handle = h
                    self.last_x, self.last_y = event.x, event.y
                    # Deselect all items unless CTRL or SHIFT is pressed
                    # or the item is already selected.
                    if not (event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK)
                            or view.hovered_item in view.selected_items):
                        del view.selected_items
                        view.focused_item = item
                    print 'Grab handle', h, 'of', item
                    return True


def DefaultToolChain():
    """The default tool chain build from HoverTool, ItemTool and HandleTool.
    """
    chain = ToolChain()
    chain.append(HoverTool())
    chain.append(ItemTool())
    return chain


if __name__ == '__main__':
    import doctest
    doctest.testmod()

# vim: sw=4:et:ai
