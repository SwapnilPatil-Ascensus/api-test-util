# Sanitized HAR Capture for Mobile/WebView Flows

1. Open Chrome DevTools and select Network.
2. Enable Preserve log if navigation clears requests.
3. Clear the network list.
4. Traverse one coherent mobile application flow from its starting screen to completion.
5. Use the DevTools export option for a sanitized HAR. Do not choose the sensitive-data export.
6. Name the file by flow and environment, for example `qc4-mobile-dashboard-sanitized.har`.
7. Place the file in a local `inputs/har/` folder that is ignored by Git.
8. Run the offline utility and review its sanitization report before retaining or sharing the HAR.

Capture separate HAR files for distinct domains when possible. This improves traceability and avoids mixing unrelated background traffic.
