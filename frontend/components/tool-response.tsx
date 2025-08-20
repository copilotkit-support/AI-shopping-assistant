import React from 'react';

interface DialogBoxProps {
  contentList: { title: string; url: string }[];
  onAccept: () => void;
  onReject: () => void;
  onNeedInfo: () => void;
}

const DialogBox: React.FC<DialogBoxProps> = ({ contentList, onAccept, onReject, onNeedInfo }) => {
  return (
    <div className="border border-gray-300 rounded-lg shadow-lg w-96 max-h-96 overflow-hidden flex flex-col">
      <div className="overflow-y-auto p-4 flex-grow">
        {contentList.map((content, index) => (
          <div key={index} className="mb-3">
            <h3 className="font-semibold">{content.title}</h3>
            <a href={content.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{content.url}</a>
          </div>
        ))}
      </div>
      <div className="flex justify-between p-4 border-t border-gray-200">
        <button onClick={onAccept} className="bg-green-500 text-white py-2 px-4 rounded">Accept</button>
        <button onClick={onReject} className="bg-red-500 text-white py-2 px-4 rounded">Reject</button>
        <button onClick={onNeedInfo} className="bg-yellow-500 text-white py-2 px-4 rounded">Need Info</button>
      </div>
    </div>
  );
};

export default DialogBox;
