export default function GitHubDocsPage() {
  return (
    <>
      <h1>GitHub</h1>
      <p className="lead">
        GitHub OAuth powers repository import and pull-request creation. Disconnect anytime from the
        app chrome.
      </p>

      <h2>Create an OAuth app</h2>
      <ol>
        <li>GitHub → Settings → Developer settings → OAuth Apps → New.</li>
        <li>
          Authorization callback URL: <code>http://127.0.0.1:8000/auth/github/callback</code>
        </li>
        <li>
          Copy Client ID and Client Secret into <code>.env</code> as <code>GITHUB_CLIENT_ID</code> and{" "}
          <code>GITHUB_CLIENT_SECRET</code>.
        </li>
      </ol>

      <h2>In the product UI</h2>
      <ul>
        <li>
          Disconnected: the top bar shows <strong>Connect GitHub</strong>.
        </li>
        <li>
          Connected: the top bar shows <strong>GitHub · @login</strong> with a Disconnect action.
        </li>
      </ul>

      <h2>What OAuth enables</h2>
      <ul>
        <li>Import private and public repositories you can access</li>
        <li>Open pull requests after an approved coding task</li>
      </ul>
    </>
  );
}
