"""Actor item classes."""

from math import pi

from gaphor import UML
from gaphor.diagram.presentation import Classified, ElementPresentation
from gaphor.diagram.shapes import Box, IconBox, Text, stroke
from gaphor.diagram.support import represents
from gaphor.diagram.text import FontWeight
from gaphor.UML.recipes import stereotypes_str

HEAD = 11
ARM = 19
NECK = 10
BODY = 20


@represents(UML.Actor)
class ActorItem(Classified, ElementPresentation):
    """Actor item is a classifier in icon mode.

    Maybe it should be possible to switch to compartment mode in the
    future.
    """

    def __init__(self, diagram, id=None):
        super().__init__(diagram, id, width=ARM * 2, height=HEAD + NECK + BODY + ARM)

        self.shape = IconBox(
            Box(
                draw=draw_actor,
            ),
            Text(
                text=lambda: stereotypes_str(self.subject),
            ),
            Text(
                text=lambda: self.subject.name or "",
                style={"font-weight": FontWeight.BOLD},
            ),
        )

        self.watch("subject[NamedElement].name")
        self.watch("subject.appliedStereotype.classifier.name")


def draw_actor(box, context, bounding_box):
    """Draw actor's icon creature."""
    cr = context.cairo

    fx = bounding_box.width / (ARM * 2)
    fy = bounding_box.height / (HEAD + NECK + BODY + ARM)

    x = ARM * fx
    y = (HEAD / 2) * fy
    cy = HEAD * fy

    cr.move_to(x + HEAD * fy / 2.0, y)
    cr.arc(x, y, HEAD * fy / 2.0, 0, 2 * pi)

    cr.move_to(x, y + cy / 2)
    cr.line_to(ARM * fx, (HEAD + NECK + BODY) * fy)

    cr.move_to(0, (HEAD + NECK) * fy)
    cr.line_to(ARM * 2 * fx, (HEAD + NECK) * fy)

    cr.move_to(0, (HEAD + NECK + BODY + ARM) * fy)
    cr.line_to(ARM * fx, (HEAD + NECK + BODY) * fy)
    cr.line_to(ARM * 2 * fx, (HEAD + NECK + BODY + ARM) * fy)
    stroke(context, fill=False)
