import React, {useState} from 'react';
import ChatInterface from './components/ChatInterface';
import FileUpload from './components/FileUpload';

function App() {
  const [showFileUpload, setShowFileUpload] = useState(false);

  const handleFileSubmitted = () => {
    setShowFileUpload(false);
  };

  const handleBackToChat = () => {
    setShowFileUpload(false);
  };

  const handleShowFileUpload = () => {
    setShowFileUpload(true);
  };

  return (
    <div className='App'>
      {!showFileUpload ? (
        <ChatInterface onFileButtonClick={handleShowFileUpload} />
      ) : (
        <FileUpload onSubmit={handleFileSubmitted} onBack={handleBackToChat} />
      )}
    </div>
  );
}

export default App;
