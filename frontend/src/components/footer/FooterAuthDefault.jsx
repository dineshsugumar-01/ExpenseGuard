/*eslint-disable*/
import React from "react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <div className="z-[5] mx-auto flex w-full max-w-screen-sm flex-col items-center justify-between px-[20px] pb-4 lg:mb-6 lg:max-w-[100%] lg:flex-row xl:mb-2 xl:w-[1310px] xl:pb-6">
      <p className="mb-6 text-center text-sm text-gray-600 md:text-base lg:mb-0">
        ©{1900 + new Date().getYear()} ExpenseGuard. All Rights Reserved.
      </p>
      <ul className="flex flex-wrap items-center sm:flex-nowrap">
        <li className="mr-12">
          <Link
            to="/admin/default"
            className="text-sm text-gray-600 hover:text-gray-800 md:text-base lg:text-white lg:hover:text-white"
          >
            Dashboard
          </Link>
        </li>
        <li className="mr-12">
          <Link
            to="/admin/rules"
            className="text-sm text-gray-600 hover:text-gray-800 md:text-base lg:text-white lg:hover:text-white"
          >
            Policy Rules
          </Link>
        </li>
        <li>
          <Link
            to="/admin/models"
            className="text-sm text-gray-600 hover:text-gray-800 md:text-base lg:text-white lg:hover:text-white"
          >
            PyOD Ensembles
          </Link>
        </li>
      </ul>
    </div>
  );
}
