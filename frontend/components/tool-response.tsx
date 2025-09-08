import React from 'react';

interface DialogBoxProps {
  contentList: { title: string; url: string }[];
  onAccept: () => void;
  onReject: () => void;
  onNeedInfo: () => void;
  isDisabled: boolean;
}

const DialogBox: React.FC<DialogBoxProps> = ({ contentList, onAccept, onReject, onNeedInfo, isDisabled }) => {
  return (
    <div className="border border-gray-300 rounded-lg shadow-lg w-54 max-h-96 overflow-hidden flex flex-col">
      <div className="overflow-y-auto p-4 flex-grow">
      Here are the top 5 relevant items I found. Would you like to see them, retry, or show all found items?
      </div>
      <div className="flex justify-between p-4 border-t border-gray-200">
        <button disabled={isDisabled} onClick={onAccept} className="bg-green-500 text-white py-1 px-3 rounded-full shadow-md hover:shadow-lg transition-shadow duration-200 text-sm bg-opacity-80 backdrop-filter backdrop-blur-lg">Accept</button>
        <button disabled={isDisabled} onClick={onReject} className="bg-red-500 text-white py-1 px-3 rounded-full shadow-md hover:shadow-lg transition-shadow duration-200 text-sm bg-opacity-80 backdrop-filter backdrop-blur-lg">Reject</button>
        <button disabled={isDisabled} onClick={onNeedInfo} className="bg-yellow-500 text-white py-1 px-3 rounded-full shadow-md hover:shadow-lg transition-shadow duration-200 text-sm bg-opacity-80 backdrop-filter backdrop-blur-lg">Show All</button>
      </div>
    </div>
  );
};

export default DialogBox;
