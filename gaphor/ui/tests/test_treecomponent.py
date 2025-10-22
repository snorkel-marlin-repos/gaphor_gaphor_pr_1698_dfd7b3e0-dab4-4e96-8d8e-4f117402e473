import pytest
from gi.repository import Gtk

from gaphor import UML
from gaphor.core.modeling import Diagram
from gaphor.ui.treecomponent import TreeComponent

skip_if_gtk3 = pytest.mark.skipif(
    Gtk.get_major_version() == 3, reason="Gtk.ListView is not supported by GTK 3"
)


@pytest.fixture
def tree_component(event_manager, element_factory, modeling_language):
    tree_component = TreeComponent(event_manager, element_factory, modeling_language)
    tree_component.open()
    yield tree_component
    tree_component.close()


class ItemChangedHandler:
    def __init__(self):
        self.added = 0
        self.removed = 0
        self.positions = []

    def __call__(self, _obj, position, removed, added):
        self.positions.append(position)
        self.removed += removed
        self.added += added


@skip_if_gtk3
def test_show_item_in_tree_list_model(tree_component, element_factory):
    class_ = element_factory.create(UML.Class)
    package = element_factory.create(UML.Package)

    class_.package = package

    pos = tree_component.select_element(class_)
    tree_model = tree_component.sort_model

    assert pos == 1
    assert tree_model.get_item(0).get_item().element is package
    assert tree_model.get_item(1).get_item().element is class_


@skip_if_gtk3
def test_tree_component_remove_element(tree_component, element_factory):
    tree_model = tree_component.model.root
    element = element_factory.create(UML.Class)
    items_changed = ItemChangedHandler()
    tree_model.connect("items-changed", items_changed)

    element.unlink()

    assert tree_model.get_n_items() == 0
    assert items_changed.removed == 1


@skip_if_gtk3
def test_tree_subtree_changed(tree_component, element_factory):
    class_ = element_factory.create(UML.Class)
    package = element_factory.create(UML.Package)

    tree_model = tree_component.model
    root_model = tree_model.root
    root_model_changed = ItemChangedHandler()
    root_model.connect("items-changed", root_model_changed)

    class_.package = package

    assert root_model.get_n_items() == 1
    assert root_model_changed.added == 2
    assert root_model_changed.removed == 3  # remove + node changed


@skip_if_gtk3
def test_tree_component_add_nested_element(tree_component, element_factory):
    tree_model = tree_component.model
    class_ = element_factory.create(UML.Class)
    package = element_factory.create(UML.Package)

    class_.package = package
    package_item = tree_model.tree_item_for_element(package)
    child_model = tree_model.child_model(package_item)

    assert package_item in tree_model.root
    assert tree_model.tree_item_for_element(class_) in child_model


@skip_if_gtk3
def test_tree_component_unset_nested_element(tree_component, element_factory):
    tree_model = tree_component.model
    class_ = element_factory.create(UML.Class)
    package = element_factory.create(UML.Package)

    class_.package = package
    del class_.package
    package_item = tree_model.tree_item_for_element(package)
    class_item = tree_model.tree_item_for_element(class_)
    child_model = tree_model.child_model(package_item)

    assert package_item is not None
    assert class_item is not None
    assert child_model is None


@skip_if_gtk3
def test_tree_component_remove_nested_element(tree_component, element_factory):
    tree_model = tree_component.model
    class_ = element_factory.create(UML.Class)
    package = element_factory.create(UML.Package)

    class_.package = package
    package_item = tree_model.tree_item_for_element(package)
    assert tree_model.child_model(package_item)

    class_.unlink()

    child_model = tree_model.child_model(package_item)
    assert tree_model.tree_item_for_element(package) is not None
    assert child_model is None


@skip_if_gtk3
def test_element_name_changed(tree_component, element_factory):
    class_ = element_factory.create(UML.Class)
    tree_item = tree_component.model.tree_item_for_element(class_)

    class_.name = "foo"

    weight, style = tree_item.attributes.get_attributes()

    assert tree_item.text == "foo"
    assert weight.as_int().value == 400
    assert style.as_int().value == 0


@skip_if_gtk3
def test_element_weight_changed(tree_component, element_factory):
    diagram = element_factory.create(Diagram)
    tree_item = tree_component.model.tree_item_for_element(diagram)
    weight, style = tree_item.attributes.get_attributes()

    assert weight.as_int().value == 700
    assert style.as_int().value == 0


@skip_if_gtk3
def test_element_style_changed(tree_component, element_factory):
    class_ = element_factory.create(UML.Class)
    tree_item = tree_component.model.tree_item_for_element(class_)

    class_.isAbstract = True
    weight, style = tree_item.attributes.get_attributes()

    assert weight.as_int().value == 400
    assert style.as_int().value == 2


@skip_if_gtk3
def test_tree_component_model_ready(event_manager, element_factory, modeling_language):
    class_ = element_factory.create(UML.Class)
    package = element_factory.create(UML.Package)
    class_.package = package
    tree_component = TreeComponent(event_manager, element_factory, modeling_language)
    tree_component.open()
    tree_model = tree_component.model

    element_factory.model_ready()

    assert tree_model.tree_item_for_element(package) is not None
    assert tree_model.tree_item_for_element(class_) is None

    tree_component.close()


@skip_if_gtk3
def test_tree_model_expand_to_relationship(tree_component, element_factory):
    association = element_factory.create(UML.Association)
    package = element_factory.create(UML.Package)
    association.package = package

    pos = tree_component.select_element(association)

    selected = tree_component.selection.get_selected_item()

    assert pos == 2
    assert selected
    assert selected.get_item().element is association
