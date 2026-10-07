import { Link } from "react-router-dom";

const Footer = () => {
  return (
    <div className="flex w-full flex-col items-center justify-between px-1 pb-8 pt-3 lg:px-8 xl:flex-row">
      <h5 className="mb-4 text-center text-sm font-medium text-gray-600 sm:!mb-0 md:text-sm">
        <p className="mb-4 text-center text-sm text-gray-500 sm:!mb-0">
          ©{1900 + new Date().getYear()} ExpenseGuard. Continuous Anomaly Detection & Expense Management.
        </p>
      </h5>
      <div>
        <ul className="flex flex-wrap items-center gap-3 sm:flex-nowrap md:gap-8">
          <li>
            <Link
              to="/admin/default"
              className="text-sm font-medium text-gray-500 hover:text-brand-500 dark:text-gray-400 dark:hover:text-white"
            >
              Overview
            </Link>
          </li>
          <li>
            <Link
              to="/admin/review-queue"
              className="text-sm font-medium text-gray-500 hover:text-brand-500 dark:text-gray-400 dark:hover:text-white"
            >
              Review Queue
            </Link>
          </li>
          <li>
            <Link
              to="/admin/rules"
              className="text-sm font-medium text-gray-500 hover:text-brand-500 dark:text-gray-400 dark:hover:text-white"
            >
              Policy Rules
            </Link>
          </li>
          <li>
            <Link
              to="/admin/models"
              className="text-sm font-medium text-gray-500 hover:text-brand-500 dark:text-gray-400 dark:hover:text-white"
            >
              PyOD Ensembles
            </Link>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default Footer;
