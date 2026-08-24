import { motion } from "framer-motion";

function StatCard({ title, value }) {
  return (
    <motion.div
      whileHover={{ scale: 1.03 }}
      className="stat-card"
    >
      <h3>{title}</h3>
      <h1>{value}</h1>
    </motion.div>
  );
}

export default StatCard;