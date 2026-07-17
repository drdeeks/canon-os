"use strict";

const { createApp } = require("./app");

const port = Number.parseInt(process.env.PORT || "4000", 10);
let app;
try {
  app = createApp();
} catch (error) {
  console.error(`Unable to configure Canon OS API: ${error.message}`);
  process.exit(1);
}

app.listen(port, () => {
  console.log(`Canon OS API listening on port ${port}`);
});
