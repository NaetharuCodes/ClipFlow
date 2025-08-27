import { useState } from "react";

import "./App.css";

function App() {
  const [count, setCount] = useState(0);
  const [apiResponse, setApiResponse] = useState<string>("");

  const testAPI = async () => {
    try {
      const response = await fetch("http://localhost:8000/health");
      const data = await response.json();
      setApiResponse(`API Response: ${data.status} - ${data.service}`);
    } catch (error) {
      setApiResponse(`Error: ${error}`);
    }
  };

  return (
    <>
      <h1>MY APP</h1>
      <button onClick={testAPI}>Test API Connection</button>
      {apiResponse && <p>{apiResponse}</p>}
    </>
  );
}

export default App;
