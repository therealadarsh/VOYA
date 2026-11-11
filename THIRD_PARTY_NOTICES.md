# Third-party notices

## Daytrip (ArabotHXL/trip-planner)

Source: https://github.com/ArabotHXL/trip-planner, commit `74610afbccd23264997c28d5d77a8f8c3a7a248f`.
License: MIT (declared in the project's `package.json`; the repository ships no
LICENSE file and names no copyright holder).

What VOYA reuses: the per-price-level and per-place-type USD point values from
`artifacts/api-server/src/lib/pois.ts` (`estimateCost`), in
`src/voya/cost/estimators.py`. No code is copied; the numbers are
re-expressed in Python with VOYA's own ranges and confidences.

MIT License text (standard form):

> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in
> all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.
