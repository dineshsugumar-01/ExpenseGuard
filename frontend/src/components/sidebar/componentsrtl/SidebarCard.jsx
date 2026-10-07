import React from "react";
import { Link } from "react-router-dom";
import { MdSecurity } from "react-icons/md";

const SidebarCard = () => {
  return (
    <div className="relative mt-14 flex w-[256px] justify-center rounded-[20px] bg-gradient-to-br from-[#868CFF] via-[#432CF3] to-brand-500 pb-4 shadow-lg shadow-brand-500/20">
      <div className="absolute -top-12 flex h-20 w-20 items-center justify-center rounded-full border-[4px] border-white bg-gradient-to-b from-[#868CFF] to-brand-500 shadow-md dark:!border-navy-800">
        <MdSecurity className="h-10 w-10 text-white" />
      </div>

      <div className="mt-12 flex h-fit flex-col items-center px-4 text-center">
        <p className="text-base font-bold text-white">ExpenseGuard AI</p>
        <p className="mt-1 text-xs leading-relaxed text-white/80">
          Unsupervised PyOD engine active. Monitoring transactions & policy violations.
        </p>

        <Link
          to="/admin/review-queue"
          className="mt-4 block w-full rounded-xl bg-white/20 py-2 text-center text-xs font-bold text-white backdrop-blur-md transition-all duration-200 hover:bg-white hover:text-brand-500"
        >
          Open Review Queue
        </Link>
      </div>
    </div>
  );
};

export default SidebarCard;
