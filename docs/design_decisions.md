# Design Decisions

## Stock Status Column

- Introduces a `stock_status` column in the items table to align with the grid view.
- Uses design-system badges (`badge-error`, `badge-success`, `badge-gray`) to display **Low Stock**, **In Stock**, or **No Data** based on `current_stock` and `reorder_point`.
- Column visibility is toggleable like other columns via the column menu and remembered in local storage.
