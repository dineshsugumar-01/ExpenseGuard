import React from "react";

// Admin Views
import OverviewDashboard from "views/admin/default";
import TransactionsView from "views/admin/transactions";
import ReviewQueueView from "views/admin/review";
import RulesView from "views/admin/rules";
import ModelsView from "views/admin/models";
import ClaimSubmissionView from "views/admin/claim";

// Auth Views
import SignIn from "views/auth/SignIn";

// Icon Imports
import {
  MdHome,
  MdReceiptLong,
  MdWarning,
  MdTune,
  MdAutoAwesome,
  MdAddCircleOutline,
  MdLock,
} from "react-icons/md";

const routes = [
  {
    name: "Overview",
    layout: "/admin",
    path: "default",
    icon: <MdHome className="h-6 w-6" />,
    component: <OverviewDashboard />,
  },
  {
    name: "Transactions",
    layout: "/admin",
    path: "transactions",
    icon: <MdReceiptLong className="h-6 w-6" />,
    component: <TransactionsView />,
  },
  {
    name: "Review Queue",
    layout: "/admin",
    path: "review-queue",
    icon: <MdWarning className="h-6 w-6" />,
    component: <ReviewQueueView />,
  },
  {
    name: "Policy Rules",
    layout: "/admin",
    path: "rules",
    icon: <MdTune className="h-6 w-6" />,
    component: <RulesView />,
  },
  {
    name: "PyOD Models",
    layout: "/admin",
    path: "models",
    icon: <MdAutoAwesome className="h-6 w-6" />,
    component: <ModelsView />,
  },
  {
    name: "Submit Claim",
    layout: "/admin",
    path: "claim",
    icon: <MdAddCircleOutline className="h-6 w-6" />,
    component: <ClaimSubmissionView />,
  },
  {
    name: "Sign In",
    layout: "/auth",
    path: "sign-in",
    icon: <MdLock className="h-6 w-6" />,
    component: <SignIn />,
  },
];

export default routes;
