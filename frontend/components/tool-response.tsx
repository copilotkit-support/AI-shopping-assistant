import React from 'react';

interface DialogBoxProps {
  contentList: { title: string; url: string }[];
  onAccept: () => void;
  onReject: () => void;
  onNeedInfo: () => void;
}

const DialogBox: React.FC<DialogBoxProps> = ({ contentList, onAccept, onReject, onNeedInfo }) => {
  return (
    <div className="border border-gray-300 rounded-lg shadow-lg w-54 max-h-96 overflow-hidden flex flex-col">
      <div className="overflow-y-auto p-4 flex-grow">
        {contentList.map((content, index) => (
          <div key={index} className="mb-3 cursor-pointer border p-2 rounded shadow-sm hover:shadow-md transition-shadow duration-200" onClick={() => window.open(content.url, '_blank')}>
            <h3 className="font-semibold truncate" title={content.title}>{content.title}</h3>
          </div>
        ))}
      </div>
      <div className="flex justify-between p-4 border-t border-gray-200">
        <button onClick={onAccept} className="bg-green-500 text-white py-1 px-3 rounded-full shadow-md hover:shadow-lg transition-shadow duration-200 text-sm bg-opacity-80 backdrop-filter backdrop-blur-lg">Accept</button>
        <button onClick={onReject} className="bg-red-500 text-white py-1 px-3 rounded-full shadow-md hover:shadow-lg transition-shadow duration-200 text-sm bg-opacity-80 backdrop-filter backdrop-blur-lg">Reject</button>
        <button onClick={onNeedInfo} className="bg-yellow-500 text-white py-1 px-3 rounded-full shadow-md hover:shadow-lg transition-shadow duration-200 text-sm bg-opacity-80 backdrop-filter backdrop-blur-lg">Need Info</button>
      </div>
    </div>
  );
};

export default DialogBox;
