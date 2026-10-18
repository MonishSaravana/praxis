// praxis.monishsaravana.com: serve index.html for directory paths, and add the trailing slash to directory URLs
// so relative links inside /viewer/ and /studio/ resolve.
function handler(event) {
  var r = event.request;
  var last = r.uri.split('/').pop();
  if (r.uri.charAt(r.uri.length - 1) === '/') {
    r.uri += 'index.html';
  } else if (last.indexOf('.') === -1) {
    return { statusCode: 301, statusDescription: 'Moved Permanently', headers: { location: { value: r.uri + '/' } } };
  }
  return r;
}
