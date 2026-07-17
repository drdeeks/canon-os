"use strict";

const { createApp } = require("./app");

const port = Number.parseInt(process.env.PORT || "4000", 10);
const app = createApp();

app.listen(port, () => {
  console.log(`Canon OS API listening on port ${port}`);
});
