/* eslint-disable */

import { HiX } from "react-icons/hi";
import Links from "./components/Links";

import SidebarCard from "./components/SidebarCard";
import routes from "routes.js";
import { MdShield } from "react-icons/md";

const Sidebar = ({ open, onClose }) => {
  return (
    <div
      className={`sm:none duration-175 linear fixed !z-50 flex min-h-full flex-col bg-white pb-10 shadow-2xl shadow-white/5 transition-all dark:!bg-navy-800 dark:text-white md:!z-50 lg:!z-50 xl:!z-0 ${
        open ? "translate-x-0" : "-translate-x-96"
      }`}
    >
      <span
        className="absolute top-4 right-4 block cursor-pointer xl:hidden"
        onClick={onClose}
      >
        <HiX />
      </span>

      <div className="mx-[40px] mt-[40px] flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500 text-white shadow-md shadow-brand-500/30">
          <MdShield className="h-6 w-6" />
        </div>
        <div>
          <div className="font-poppins text-[22px] font-bold text-navy-700 dark:text-white tracking-tight leading-none">
            Expense<span className="text-brand-500">Guard</span>
          </div>
          <div className="mt-1 text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-400">
            Anomaly Detection
          </div>
        </div>
      </div>
      <div className="mt-[32px] mb-6 h-px bg-gray-200 dark:bg-white/10" />
      {/* Nav item */}

      <ul className="mb-auto pt-1">
        <Links routes={routes} />
      </ul>

      {/* ExpenseGuard AI Card */}
      <div className="flex justify-center">
        <SidebarCard />
      </div>

      {/* Nav item end */}
    </div>
  );
};

export default Sidebar;
